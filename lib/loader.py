"""
.. py:module:: loader.py
   :synopsis: .

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
from collections import defaultdict
import logging
import os
import sys

from argparse import ArgumentParser
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import and_
from orm import GeneName, GeneSymbol, Database, Gene, initdb

class Namespace:
    # general DBs
    uniprot = 'prot'
    ensemble = 'ensg'
    entrez = 'gi'
    # organism-specific DBs
    hgnc = 'hgnc' # human
    mgd = 'mgi' # mouse
    rgd = 'rgd' # rat
    flybase = 'fly' # fly
    sgd = 'sgd' # yeast
    tair = 'tair' # cress
    ecocyc = 'eco' # e.coli
    wormbase = 'wb' # nematode
    xenbase = 'xb' # frog

NAMESPACES = frozenset({
    Namespace.uniprot,
    Namespace.ensemble,
    Namespace.entrez,
    Namespace.hgnc,
    Namespace.mgd,
    Namespace.rgd,
    Namespace.flybase,
    Namespace.sgd,
    Namespace.tair,
    Namespace.ecocyc,
    Namespace.wormbase,
    Namespace.xenbase,
})

class Species:
    human = 9606
    mouse = 10090
    rat = 10116
    fly = 7227
    yeast = 4932
    cress = 3702
    e_coli = 562
    nematode = 6239
    frog = 8355

SPECIES = frozenset({
    Species.human,
    Species.mouse,
    Species.rat,
    Species.fly,
    Species.yeast,
    Species.cress,
    Species.e_coli,
    Species.nematode,
    Species.frog,
})

class Record:
    """
    The abstract representation of a gene/protein name record to store.

    This representation is used by the `loader.load` function to add any
    relevant novel data to the DB.
    """

    def __init__(self, namespace:str, accession:str, species_id:int,
                 symbol:str=None, name:str=None):
        """
        Initialize with the `Namespace` and accession of that record, the
        official symbol and name of that gene/protein as found in the
        originating DB, and the species ID for that record.

        Add additional `symbols` and `names` as strings after initialization
        to the corresponding sets.

        Both the set of `links` and `references` are (namespace, accession)
        tuples. As required, add `links` to existing `orm.Database` objects,
        and add `references` to create new ones.
        """
        self.namespace = namespace
        self.accession = accession
        self.symbol = symbol
        self.name = name
        self.species_id = species_id
        self.symbols = set()
        self.names = set()
        self.links = set()
        self.references = set()
        self.namespaces = set()
        self.accessions = set()
        self._addNsAcc(namespace, accession)

        if symbol:
            self.symbols.add(symbol)

        if name:
            self.names.add(name)

    def _addNsAcc(self, ns, acc):
        assert ns in NAMESPACES, "namespace '" + ns + "' unknown"
        self.namespaces.add(ns)
        self.accessions.add(acc)

    def addLink(self, namespace, accession):
        self.links.add((namespace, accession))
        self._addNsAcc(namespace, accession)

    def addReference(self, namespace, accession):
        self.references.add((namespace, accession))
        self._addNsAcc(namespace, accession)

def dereference(args):
    """
    Yield the namespaces that should be used for linking according to the
    command line arguments `args`.
    """
    for ns in NAMESPACES:
        if getattr(args, ns): yield ns

def loadGeneRecord(session:Session, record:Record,
                   location:str=None, chromosome:str=None):
    """
    Load the `Record` data into the database.

    :param session: an SQL Alchemy DB session
    :param record: a `Record` representation of the parsed data
    :param location: the chromosome location for this `record` if any
    :param chromosome: the chromosome (name, number, ...) for this `record`
                       if any
    """
    # TODO: make another such function for protein DB loaders
    logging.debug('loading %s:%s', record.namespace, record.accession)

    db_objects = dict() # list of all Database objects loaded, keyed by ns, acc

    db_record = None # the Database object for this Record

    # the ns, acc key for this Database object/Record
    record_ns_acc = (record.namespace, record.accession)

    # sets of Database ns, acc keys, grouped by their associated gene IDs
    gene_id2ns_acc = defaultdict(set)

    # Strategy: load *everything* relevant to the Record in one huge query
    for db in session.query(Database).options(
        joinedload(Database.genes),
        joinedload('genes.symbols'),
        joinedload('genes.names'),
    ).filter(and_(Database.namespace.in_(record.namespaces),
                  Database.accession.in_(record.accessions))):
        key = (db.namespace, db.accession)
        db_objects[key] = db

        for g in db.genes:
            gene_id2ns_acc[g.id].add(key)

    logging.debug('loaded %s Database objects', len(db_objects))

    # get or create the Database object for this Record
    if record_ns_acc not in db_objects:
        logging.debug('creating new Database object %s:%s', *record_ns_acc)
        db_record = Database(
            record.namespace, record.accession,
            symbol=record.symbol, name=record.name
        )
        session.add(db_record)
        db_objects[record_ns_acc] = db_record
    else:
        db_record = db_objects[record_ns_acc]

    # iterate over all relevant Gene objects and add new data
    for g in _gene_iter(db_objects, db_record, session, record,
                       chromosome=chromosome, location=location):
        logging.debug('started updating %s', g)
        known = gene_id2ns_acc[g.id]

        if record_ns_acc not in known:
            logging.debug('adding %s to %s set', db_record, g)
            g.records.append(db_record)

        for ns_acc in record.references.difference(known):
            if ns_acc in db_objects:
                db_ref = db_objects[ns_acc]
            else:
                logging.debug('creating new Database object %s:%s', *ns_acc)
                db_ref = Database(*ns_acc)
                session.add(db_ref)

            logging.debug('linking %s to %s', db_ref, g)
            g.records.append(db_ref)

        known = set(s.symbol for s in g.symbols)

        for sym in record.symbols.difference(known):
            logging.debug('creating new GeneSymbol %s for %s', sym, g)
            g.symbols.append(GeneSymbol(g.id, sym))

        known = set(n.name for n in g.names)

        for name in record.names.difference(known):
            logging.debug('creating new GeneName %s for %s', name, g)
            g.names.append(GeneName(g.id, name))

        logging.debug('finished updating %s', g)

    session.flush()

def _gene_iter(db_objects, db_record, session, record,
               chromosome=None, location=None):
    genes = set(db_record.genes)

    # load any potential genes for this record
    for ns_acc in record.links:
        if ns_acc in db_objects:
            for g in db_objects[ns_acc].genes:
                if not g.location and location:
                    g.location = location

                if not g.chromosome and chromosome:
                    g.chromosome = chromosome

                assert g.species_id == record.species_id,\
                "species {} mismatch for {}".format(record.species_id,
                                                    repr(g))
                genes.add(g)
    if not genes:
        # create a new gene
        logging.debug("creating a new gene for %s:%s",
                      record.namespace, record.accession)
        g = Gene(record.species_id, location=location, chromosome=chromosome)
        session.add(g)
        genes.add(g)
    elif len(genes) > 1:
        # issue a warning that more than one gene was found
        if record.links:
            links = ", {}".format(", ".join(
                "{}:{}".format(ns, acc) for ns, acc in record.links
            ))
        else:
            links = ""

        logging.warn(
            "%i genes (%s) found for %s:%s%s",
            len(genes),
            ", ".join(str(g.id) for g in genes),
            record.namespace, record.accession, links
        )

    return iter(genes)

def argparser(synopsis:str, version:str, usage="%(prog)s [options] <FILE>"):
    """
    Create a new `argparse.ArgumentParser` object.

    :param synopsis: a short summary of the loader's functionality
    :param version: the version of the loader
    :param usage: the usage string for this loader (default: single file)
    """
    parser = ArgumentParser(
        usage=usage, description=synopsis,
        prog=os.path.basename(sys.argv[0]),
        epilog="version " + version
    )

    parser.set_defaults(loglevel=logging.WARNING)

    parser.add_argument(
        '-e', '--encoding', action='store',
        default=sys.getdefaultencoding(),
        help="read files using specified encoding [%(default)s]"
    )
    parser.add_argument(
        '-d', '--database', action='store',
        default=os.getenv('PGDATABASE', "gnamed"),
        help="database name [%(default)s]"
    )
    parser.add_argument(
        '--host', action='store',
        default=os.getenv('PGHOST', "localhost"),
        help="database host [%(default)s]"
    )
    parser.add_argument(
        '--port', action='store', type=int,
        default=int(os.getenv('PGPORT', "5432")),
        help="database port [%(default)s]"
    )
    parser.add_argument(
        '--driver', action='store',
        default='postgresql+psycopg2',
        help="database driver [%(default)s]"
    )
    parser.add_argument(
        '-u', '--username', action='store',
        default=os.getenv('PGUSER'),
        help="database username [%(default)s]"
    )
    parser.add_argument(
        '-p', '--password', action='store',
        default=os.getenv('PGPASSWORD'),
        help="database password [%(default)s]"
    )
    parser.add_argument(
        '--' + Namespace.entrez, action='store_true',
        help="link to existing Entrez Gene IDs"
    )
    parser.add_argument(
        '--' + Namespace.uniprot, action='store_true',
        help="link to existing UniProt IDs"
    )
    parser.add_argument(
        '--' + Namespace.ensemble, action='store_true',
        help="link to existing Ensemble IDs"
    )
    parser.add_argument(
        '--' + Namespace.hgnc, action='store_true',
        help="link to existing HGNC (human) IDs"
    )
    parser.add_argument(
        '--' + Namespace.mgd, action='store_true',
        help="link to existing MGD (mouse) IDs"
    )
    parser.add_argument(
        '--' + Namespace.rgd, action='store_true',
        help="link to existing RGD (rat) IDs"
    )
    parser.add_argument(
        '--' + Namespace.flybase, action='store_true',
        help="link to existing FlyBase (fruit fly) IDs"
    )
    parser.add_argument(
        '--' + Namespace.sgd, action='store_true',
        help="link to existing SGD (yeast) IDs"
    )
    parser.add_argument(
        '--' + Namespace.ecocyc, action='store_true',
        help="link to existing EcoCyc (E. coli) IDs"
    )
    parser.add_argument(
        '--' + Namespace.tair, action='store_true',
        help="link to existing TAIR (thale cress) IDs"
    )
    parser.add_argument(
        '--' + Namespace.wormbase, action='store_true',
        help="link to existing WormBase (nematode) IDs"
    )
    parser.add_argument(
        '--' + Namespace.xenbase, action='store_true',
        help="link to existing XenBase (frog) IDs"
    )
    parser.add_argument(
        '--error', action='store_const', const=logging.ERROR,
        dest='loglevel', help="set log level error [warn]"
    )
    parser.add_argument(
        '--info', action='store_const', const=logging.INFO,
        dest='loglevel', help="set log level info [warn]"
    )
    parser.add_argument(
        '--debug', action='store_const', const=logging.DEBUG,
        dest='loglevel', help="set log level debug [warn]"
    )
    parser.add_argument(
        '--logfile', metavar="FILE", help="log to file, not STDERR"
    )

    return parser

def setup(db_url:URL, loglevel:int, logfile:str=None):
    logging.basicConfig(
        filename=logfile, level=loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    if loglevel <= logging.DEBUG:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    logging.info("connecting to %s", db_url)
    initdb(db_url)

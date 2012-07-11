"""
.. py:module:: libgnamed.loader
   :synopsis: load gene/protein name repository records into a gnamed DB

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import sys

from collections import defaultdict
from libgnamed.parsers import AbstractParser
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import and_

from libgnamed.orm import GeneName, GeneSymbol, Database, Gene

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

    This representation is used by the Parsers' loadRecord methods to add any
    relevant, novel data to the DB.
    """

    def __init__(self, namespace:str, accession:str, species_id:int,
                 version:str=None, symbol:str=None, name:str=None):
        """
        Initialize with the `Namespace` and accession of that record, the
        official symbol and name of that gene/protein as found in the
        originating DB, and the species ID for that record.

        Add additional `symbols` and `names` as strings after initialization
        to these corresponding sets.

        The set of `links` is a collection of (namespace, accession)
        tuples. Add `links` to other records in other namespaces after
        initialization using the `Record.addLink` method.

        Note that, while proteins have lengths and masses and genes have
        locations and chromosomes, this data is handled directly in the parsers
        and is not added to the `Record` instances.
        """
        self.namespace = namespace
        self.accession = accession
        self.version = version
        self.symbol = symbol
        self.name = name
        self.species_id = species_id
        self.symbols = set()
        self.names = set()
        self.links = set()
        self.namespaces = set()
        self.accessions = set()

        if symbol:
            self.symbols.add(symbol)

        if name:
            self.names.add(name)

class AbstractProteinParser(AbstractParser):
    """
    A (still) abstract parser that can be used to load Protein records into the
    database.

    This parser should only be implemented for protein-centric repositories
    such as UniProt.
    """

    def __init__(self, *files:str, encoding:str=sys.getdefaultencoding()):
        """
        :param files: any number of files (pathnames) to load
        :param encoding: the character encoding used by these files
        """
        super(AbstractProteinParser, self).__init__(*files, encoding=encoding)
        self.db_objects = {}

    #noinspection PyUnusedLocal
    def loadRecord(self, record:Record, length:int=None, mass:int=None):
        """
        Load a repository `Record` into the database.

        :param record: a `Record` representation of the parsed data
        :param length: the length (AA) for this protein (if known)
        :param mass: the mass (kDa) for this `record` (if known)
        """
        # TODO
        pass

class AbstractGeneParser(AbstractParser):
    """
    A (still) abstract parser that can be used to load Gene records into the
    database.

    This parser should be implemented for all repositories but protein-centric
    databases such as UniProt.
    """

    def __init__(self, *files:str, encoding:str=sys.getdefaultencoding()):
        """
        :param files: any number of files (pathnames) to load
        :param encoding: the character encoding used by these files
        """
        super(AbstractGeneParser, self).__init__(*files, encoding=encoding)
        self.db_objects = {}

    def loadRecord(self, record:Record,
                   location:str=None, chromosome:str=None):
        """
        Load a repository `Record` into the database.

        :param record: a `Record` representation of the parsed data
        :param location: the chromosome location for the associated gene (if
                         known)
        :param chromosome: the chromosome (name, number, ...) for the
                           associated gene (if known)
        """
        logging.debug('loading %s:%s', record.namespace, record.accession)

        # the ns, acc key for this Database object/Record
        db_key = (record.namespace, record.accession)

        # set of ns, acc keys that have not yet been loaded
        missing_db_keys = set(
            ns_acc for ns_acc in record.links if ns_acc not in self.db_objects
        )
        existing_db_keys = record.links.difference(missing_db_keys)

        if db_key not in self.db_objects:
            missing_db_keys.add(db_key)
        else:
            existing_db_keys.add(db_key)

        # split the keys into two lists of namespaces and accessions
        ns_list, acc_list = zip(*missing_db_keys)

        # load *everything* relevant to the current Record in one large query
        for db in self.session.query(Database).options(
            joinedload(Database.genes),
            joinedload('genes.symbols'),
            joinedload('genes.names'),
        ).filter(and_(Database.namespace.in_(ns_list),
                      Database.accession.in_(acc_list))):
            key = (db.namespace, db.accession)
            self.db_objects[key] = db

            if key in missing_db_keys:
                missing_db_keys.remove(key)
                existing_db_keys.add(key)

        # sets of Database keys grouped by their associated gene IDs
        gene_id2db_keys = defaultdict(set)

        # get or create the Database object for this Record
        if db_key in missing_db_keys:
            logging.debug('creating new Database object %s:%s', *db_key)
            missing_db_keys.remove(db_key)
            db_object = Database(
                record.namespace, record.accession, version=record.version,
                symbol=record.symbol, name=record.name
            )
            self.session.add(db_object)
            self.db_objects[db_key] = db_object
        else:
            existing_db_keys.remove(db_key)
            db_object = self.db_objects[db_key]
            db_object.symbol = record.symbol
            db_object.name = record.name

        # create any missing, linked Database objects
        for ns_acc in missing_db_keys:
            logging.debug('creating new Database object %s:%s', *ns_acc)
            db = Database(*ns_acc)
            self.session.add(db)
            self.db_objects[ns_acc] = db

        # relevant genes
        genes = set(db_object.genes)

        # gene ID to linked DB objects mappings for existing DB objects and
        # define the relevant genes (usually, only one) for this record
        for ns_acc in tuple(existing_db_keys):
            if ns_acc[0] == Namespace.uniprot:
                # do not add protein links to genes
                existing_db_keys.remove(ns_acc)
                continue

            for g in self.db_objects[ns_acc].genes:
                if g.species_id != record.species_id:
                    # do not iterate links to genes of other species
                    existing_db_keys.remove(ns_acc)
                    continue

                gene_id2db_keys[g.id].add(ns_acc)

                if not g.location and location:
                    g.location = location

                if not g.chromosome and chromosome:
                    g.chromosome = chromosome

                genes.add(g)

        if not genes:
            # create a new gene
            logging.debug("creating a new gene for %s", db_object)
            g = Gene(record.species_id, location=location,
                     chromosome=chromosome)
            self.session.add(g)
            genes.add(g)
        elif len(genes) > 1:
            # issue a warning that more than one gene was found
            link_str = ", {}".format(", ".join(
                "{}:{}".format(ns, acc) for ns, acc in existing_db_keys
            )) if existing_db_keys else ""
            logging.warn(
                "%i genes (%s) found for %s%s", len(genes),
                ", ".join(str(g.id) for g in genes), db_object, link_str
            )
        # iterate over all relevant Gene objects and add new data
        for g in genes:
            logging.debug('started updating %s', g)
            known = gene_id2db_keys[g.id]

            if db_key not in known:
                logging.debug('adding %s to %s set', db_object, g)
                g.records.append(db_object)

            for ns_acc in record.links.difference(known):
                logging.debug('linking %s:%s to %s', ns_acc[0], ns_acc[1], g)
                db_obj = self.db_objects[ns_acc]
                g.records.append(db_obj)

            for sym in record.symbols.difference(s.symbol for s in g.symbols):
                logging.debug('adding symbol="%s" to %s', sym, g)
                g.symbols.append(GeneSymbol(g.id, sym))

            for name in record.names.difference(n.name for n in g.names):
                logging.debug('adding name="%s" to %s', name, g)
                g.names.append(GeneName(g.id, name))

            logging.debug('finished updating %s', g)

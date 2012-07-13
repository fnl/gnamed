"""
.. py:module:: libgnamed.parsers.entrez
   :synopsis: NCBI Entrez gene_info file parser

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import io

from collections import namedtuple
from sqlalchemy.schema import Sequence

from libgnamed.constants import Namespace
from libgnamed.loader import Record, AbstractGeneParser
from libgnamed.parsers import AbstractParser

Line = namedtuple('Line', [
    'species_id', 'id',
    'symbol', 'locus_tag', 'synonyms', 'dbxrefs', 'chromosome',
    'map_location', 'name', 'type_of_gene', 'nomenclature_symbol',
    'nomenclature_name', 'nomenclature_status', 'other_designations',
    'modification_date'
])

# name of each column on a Line (for debugging)
COLNAME = {
    0: 'species_id',
    1: 'id',
    2: 'symbol',
    3: 'locus_tag',
    4: 'synonyms',
    5: 'dbxrefs',
    6: 'chromosome',
    7: 'map_loaction',
    8: 'name',
    9: 'type_of_gene',
    10: 'nomenclature_symbol',
    11: 'nomenclature_name',
    12: 'nomenclature_status',
    13: 'other_designations',
    14: 'modification_date',
    }

# frequently found names in Entrez that are complete trash
# fields: synonyms, name, nomenclature name, other designations
JUNK_NAMES = frozenset([
    'hypothetical protein',
    'polypeptide',
    'polyprotein',
    'predicted protein',
    'protein',
    'pseudo',
    'similar to predicted protein',
    'similar to conserved hypothetical protein',
    'similar to hypothetical protein',
    'similar to polypeptide',
    'similar to polyprotein',
    'similar to predicted protein',
    ])

# "translation" of dbxref names to the local Namespace names
TRANSLATE = {
    'Ensembl': Namespace.ensemble,
    'FLYBASE': Namespace.flybase,
    'HGNC': Namespace.hgnc,
    'MGI': Namespace.mgd,
    'RGD': Namespace.rgd,
    'SGD': Namespace.sgd,
    'UniProtKB/Swiss-Prot': Namespace.uniprot,
    'TAIR': Namespace.tair,
    'ECOCYC': Namespace.ecocyc,
    'WormBase': Namespace.wormbase,
    'Xenbase': Namespace.xenbase,

    'AnimalQTLdb': None,
    'APHIDBASE': None,
    'ApiDB_CryptoDB': None,
    'BEEBASE': None,
    'BEETLEBASE': None,
    'BGD': None,
    'CGNC': None,
    'dictyBase': None,
    'EcoGene': None,
    'HPRD': None,
    'HPRDmbl': None,
    'IMGT/GENE-DB': None,
    'InterPro': None,
    'MaizeGDB': None,
    'MIM': None,
    'MIMC': None,
    'miRBase': None,
    'NASONIABASE': None,
    'Pathema': None,
    'PBR': None,
    'PFAM': None,
    'PseudoCap': None,
    'VBRC': None,
    'VectorBase': None,
    'Vega': None,
    'Vegambl': None,
    'ZFIN': None,

    }

def isGeneSymbol(sym:str) -> bool:
    """
    Return ``true`` if `sym` fits into a GeneSymbol field and has no spaces.
    """
    return len(sym) < 65 and " " not in sym

class EntrezParserMixin:

    def _parse(self, line:str):
        # remove the backslash junk in the Entrez data file
        idx = line.find('\\')

        while idx != -1:
            if len(line) > idx + 1 and line[idx+1].isalnum():
                line = '{}/{}'.format(line[:idx], line[idx+1:])
            else:
                line = '{}{}'.format(line[:idx], line[idx+1:])

            idx = line.find('\\', idx)

        items = [i.strip() for i in line.split('\t')]

        # ignore the undocumented "NEWENTRY" junk in the file
        if items[2] == 'NEWENTRY':
            return 0

        for idx in range(len(items)):
            if items[idx] == '-': items[idx] = ""

        # remove any junk names from the official names/symbols
        for idx in [2, 8, 10, 11]:
            if items[idx] and items[idx].lower() in JUNK_NAMES:
                logging.debug(
                    'removing %s "%s" from %s:%s',
                    COLNAME[idx], items[idx], Namespace.entrez, items[1]
                )
                items[idx] = ""

        row = Line._make(items)
        # example of a bad symbol: gi:835054 (but accepted)
        assert not row.symbol or len(row.symbol) < 65,\
        '{}:{} has an illegal symbol="{}"'.format(
            Namespace.entrez, row.id, row.symbol
        )
        record = Record(Namespace.entrez, row.id, row.species_id,
                        symbol=row.symbol, name=row.name)

        # separate existing DB links and new DB references
        if row.dbxrefs:
            for xref in row.dbxrefs.split('|'):
                db, acc = xref.split(':')

                try:
                    if TRANSLATE[db]:
                        record.links.add((TRANSLATE[db], acc))
                except KeyError:
                    logging.warn('unknown dbXref to "%s"', db)

        # parsed symbol strings
        if row.nomenclature_symbol:
            record.symbols.add(row.nomenclature_symbol)

        if row.locus_tag:
            record.symbols.add(row.locus_tag)

        if row.synonyms:
            # clean up the synonym mess, moving names to where they
            # belong, e.g., gi:814702 cites "cleavage and polyadenylation
            # specificity factor 73 kDa subunit-II" as a gene symbol
            for sym in row.synonyms.split('|'):
                sym = sym.strip()

                if sym != "unnamed" and sym.lower() not in JUNK_NAMES:
                    if isGeneSymbol(sym) or len(sym) < 17:
                        record.symbols.add(sym)
                    else:
                        record.names.add(sym)

        # parsed name strings
        if row.nomenclature_name:
            record.names.add(row.nomenclature_name)

        if row.other_designations:
            # as with synonyms, at least skip the most frequent junk
            for name in row.other_designations.split('|'):
                name = name.strip()

                if name.lower() not in JUNK_NAMES:
                    if isGeneSymbol(name):
                        record.symbols.add(name)
                    else:
                        record.names.add(name)

        # parsed keyword strings
        if row.type_of_gene and row.type_of_gene != 'other':
            record.keywords.add(row.type_of_gene)

        self.loadRecord(record, chromosome=row.chromosome,
                        location=row.map_location)
        return 1


class SpeedLoader(EntrezParserMixin, AbstractParser):
    # note: this approach is actually generic and not entrez specific
    # however, so far there is no reason to use this approach for any
    # other database
    # furthermore, apart from "dump", and "connect", the approaches should be DB
    # agnositc and might be reused to write SpeedLoaders for other DBs

    def setDSN(self, dsn:str):
        self._dsn = dsn

    def _setup(self, stream:io.TextIOWrapper):
        self._gene_id = self.session.execute(Sequence('genes_id_seq'))
        self._databases = io.StringIO()
        self._genes = io.StringIO()
        self._db2g = io.StringIO()
        self._gene_symbols = io.StringIO()
        self._gene_names = io.StringIO()
        self._gene_keywords = io.StringIO()
        self._links = set()
        self._connect()
        logging.debug("file header:\n%s", stream.readline().strip())
        return 1

    def _connect(self):
        import psycopg2
        self._conn = psycopg2.connect(self._dsn)

    def _dump(self):
        cur = self._conn.cursor()
        stream = lambda buffer: io.StringIO(buffer.getvalue())

        try:
            cur.copy_from(stream(self._databases), 'databases')
            cur.copy_from(stream(self._genes), 'genes')
            cur.copy_from(stream(self._gene_names), 'gene_names')
            cur.copy_from(stream(self._gene_symbols), 'gene_symbols')
            cur.copy_from(stream(self._gene_keywords), 'gene_keywords')
            cur.copy_from(stream(self._db2g), 'db_accessions2gene_ids')
            cur.execute("ALTER SEQUENCE genes_id_seq RESTART WITH %s",
                (self._gene_id,))
        finally:
            cur.close()

    def _flush(self):
        self._dump()
        self._databases = io.StringIO()
        self._genes = io.StringIO()
        self._db2g = io.StringIO()
        self._gene_symbols = io.StringIO()
        self._gene_names = io.StringIO()
        self._gene_keywords = io.StringIO()

    def _cleanup(self, stream:io.TextIOWrapper):
        self._dump()
        self._conn.commit()
        self._conn.close()
        return 0

    def loadRecord(self, record:Record,
                   chromosome:str=None, location:str=None):
        gid = str(self._gene_id)
        self._genes.write('{}\t{}\t{}\t{}\n'.format(
            gid, str(record.species_id),
            '\\N' if chromosome is None else chromosome,
            '\\N' if location is None else location
        ))
        self._databases.write('{}\t{}\t{}\t{}\t{}\n'.format(
            record.namespace, record.accession,
            '\\N' if record.version is None else record.version,
            '\\N' if record.symbol is None else record.symbol,
            '\\N' if record.name is None else record.name
        ))
        self._db2g.write('{}\t{}\t{}\n'.format(
            record.namespace, record.accession, gid
        ))

        for ns_acc in record.links:
            if ns_acc not in self._links:
                self._databases.write(
                    '{}\t{}\t\\N\t\\N\t\\N\n'.format(*ns_acc)
                )
                self._links.add(ns_acc)

            self._db2g.write('{}\t{}\t{}\n'.format(ns_acc[0], ns_acc[1], gid))

        for symbol in record.symbols:
            self._gene_symbols.write('{}\t{}\n'.format(gid, symbol))

        for name in record.names:
            self._gene_names.write('{}\t{}\n'.format(gid, name))

        for kwd in record.keywords:
            self._gene_keywords.write('{}\t{}\n'.format(gid, kwd))

        self._gene_id += 1

class Parser(EntrezParserMixin, AbstractGeneParser):
    """
    A parser for NCBI Entrez Gene gene_info records.
    """

    def _setup(self, stream:io.TextIOWrapper):
        logging.debug("file header:\n%s", stream.readline().strip())
        return 1


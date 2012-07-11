"""
.. py:module:: libgnamed.parsers.entrez
   :synopsis: NCBI Entrez gene_info file parser

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
from collections import namedtuple
import io
from libgnamed.loader import Namespace, Record, AbstractGeneParser
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
}

def isGeneSymbol(sym:str) -> bool:
    """
    Return ``true`` if `sym` fits into a GeneSymbol field and has no spaces.
    """
    return len(sym) < 65 and " " not in sym

class EntrezParserMixin:

    def _parse(self, line:str):
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

                if db in TRANSLATE:
                    record.links.add((TRANSLATE[db], acc))

        # parsed symbol strings
        if row.nomenclature_symbol:
            record.symbols.add(row.nomenclature_symbol)

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

        self.loadRecord(record, chromosome=row.chromosome)
        return 1

    def loadRecord(self, record:Record, chromosome:str=None, location:str=None):
        raise NotImplementedError('mixin')


class SpeedLoader(EntrezParserMixin, AbstractParser):

    def setDSN(self, dsn:str):
        self._dsn = dsn

    def _setup(self, stream:io.TextIOWrapper):
        self._gene_id = 1
        self._gene_names = io.StringIO()
        self._gene_symbols = io.StringIO()
        self._genes = io.StringIO()
        self._databases = io.StringIO()
        self._db2g = io.StringIO()
        self._links = set()
        logging.debug("file header:\n%s", stream.readline().strip())
        return 1

    def _cleanup(self, stream:io.TextIOWrapper):
        import psycopg2

        for ns, acc in self._links:
            self._databases.write('\t'.join((ns, acc, '\\N\t\\N\t\\N')))
            self._databases.write('\n')

        conn = psycopg2.connect(self._dsn)
        cur = conn.cursor()
        get = lambda buffer: io.StringIO(buffer.getvalue())

        try:
            cur.copy_from(get(self._databases), 'databases')
            cur.copy_from(get(self._genes), 'genes')
            cur.copy_from(get(self._gene_names), 'gene_names')
            cur.copy_from(get(self._gene_symbols), 'gene_symbols')
            cur.copy_from(get(self._db2g), 'db_accessions2gene_ids')
            cur.execute("ALTER SEQUENCE genes_id_seq RESTART WITH %s",
                        (self._gene_id,))
            conn.commit()
        finally:
            cur.close()
            conn.close()

        return 0 # default: no record has been added

    def loadRecord(self, record:Record, chromosome:str=None, location:str=None):
        gid = str(self._gene_id)
        self._genes.write('\t'.join((
            gid, str(record.species_id),
            '\\N' if location is None else location,
            '\\N' if chromosome is None else chromosome
        )))
        self._genes.write('\n')
        self._databases.write('\t'.join((
            record.namespace, record.accession, '\\N',
            '\\N' if record.symbol is None else record.symbol,
            '\\N' if record.name is None else record.name
        )))
        self._databases.write('\n')
        self._links.update(record.links)
        self._db2g.write('\t'.join((
            record.namespace, record.accession, gid
        )))
        self._db2g.write('\n')

        for ns, acc in record.links:
            self._db2g.write('\t'.join((ns, acc, gid)))
            self._db2g.write('\n')

        for symbol in record.symbols:
            self._gene_symbols.write('\t'.join((gid, symbol)))
            self._gene_symbols.write('\n')

        for name in record.names:
            self._gene_names.write('\t'.join((gid, name)))
            self._gene_names.write('\n')

        self._gene_id += 1

class Parser(AbstractGeneParser, EntrezParserMixin):
    """
    A parser for NCBI Entrez Gene gene_info records.
    """

    def _setup(self, stream:io.TextIOWrapper):
        logging.debug("file header:\n%s", stream.readline().strip())
        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        return 0

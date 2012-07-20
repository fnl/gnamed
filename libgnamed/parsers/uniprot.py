"""
.. py:module:: uniprot
   :synopsis: A parser for UniProtKB text files.

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import re
import io
import logging

from libgnamed.constants import Namespace
from libgnamed.loader import ProteinRecord, AbstractLoader, DBRef
from sqlalchemy.schema import Sequence

def translate_BioCyc(items:list):
    ns, acc = items[0].split(':')

    if ns == 'EcoCyc':
        yield DBRef(Namespace.ecocyc, acc)


def translate_FlyBase(items:list):
    yield DBRef(Namespace.flybase, items[0])


def translate_GeneID(items:list):
    yield DBRef(Namespace.entrez, items[0])


def translate_HGNC(items:list):
    assert items[0].startswith('HGNC:'), items
    yield DBRef(Namespace.hgnc, items[0].split(':')[1])


def translate_MGI(items:list):
    assert items[0].startswith('MGI:'), items
    yield DBRef(Namespace.hgnc, items[0].split(':')[1])


def translate_RGD(items:list):
    yield DBRef(Namespace.rgd, items[0])


def translate_SGD(items:list):
    yield DBRef(Namespace.sgd, items[0])


def translate_TAIR(items:list):
    yield DBRef(Namespace.tair, items[0])


def translate_WormBase(items:list):
    yield DBRef(Namespace.wormbase, items[0])


def translate_Xenbase(items:list):
    yield DBRef(Namespace.xenbase, items[0])


TRANSLATE = {
    '2DBase-Ecoli': None,
    'Aarhus/Ghent-2DPAGE': None,
    'Allergome': None,
    'ArachnoServer': None,
    'ArrayExpress': None,
    'AGD': None,
    'ANU-2DPAGE': None,
    'Bgee': None,
    'BindingDB': None,
    'BioCyc': translate_BioCyc,
    'BRENDA': None,
    'CAZy': None,
    'CGD': None,
    'CleanEx': None,
    'COMPLUYEAST-2DPAGE': None,
    'ConoServer': None,
    'Cornea-2DPAGE': None,
    'CTD': None,
    'CYGD': None,
    'dictyBase': None,
    'DIP': None,
    'DMDM': None,
    'DNASU': None,
    'DOSAC-COBS-2DPAGE': None,
    'DisProt': None,
    'DrugBank': None,
    'EchoBASE': None,
    'ECO2DBASE': None,
    'EcoGene': None,
    'eggNOG': None,
    'EMBL': None,
    'Ensembl': None,
    'EnsemblBacteria': None,
    'EnsemblFungi': None,
    'EnsemblMetazoa': None,
    'EnsemblPlants': None,
    'EnsemblProtists': None,
    'euHCVdb': None,
    'EuPathDB': None,
    'EvolutionaryTrace': None,
    'FlyBase': translate_FlyBase,
    'Gene3D': None,
    'GeneCards': None,
    'GeneFarm': None,
    'GeneID': translate_GeneID,
    'GenomeReviews': None,
    'GeneTree': None,
    'Genevestigator': None,
    'GenoList': None,
    'GermOnline': None,
    'GlycoSuiteDB': None,
    'GO': None,
    'Gramene': None,
    'HGNC': translate_HGNC,
    'H-InvDB': None,
    'HAMAP': None,
    'HOGENOM': None,
    'HOVERGEN': None,
    'HPA': None,
    'HSSP': None,
    'InParanoid': None,
    'IntAct': None,
    'InterPro': None,
    'IPI': None,
    'KEGG': None,
    'KO': None,
    'LegioList': None,
    'Leproma': None,
    'MaizeGDB': None,
    'MEROPS': None,
    'MGI': translate_MGI,
    'MIM': None,
    'MINT': None,
    'NextBio': None,
    'neXtProt': None,
    'OGP': None,
    'OMA': None,
    'Orphanet': None,
    'OrthoDB': None,
    'PANTHER': None,
    'PATRIC': None,
    'PDB': None,
    'PDBsum': None,
    'PeptideAtlas': None,
    'PeroxiBase': None,
    'Pfam': None,
    'PharmGKB': None,
    'PHCI-2DPAGE': None,
    'Pathway_Interaction_DB': None,
    'PhosphoSite': None,
    'PhosSite': None,
    'PhylomeDB': None,
    'PIR': None,
    'PIRSF': None,
    'PMAP-CutDB': None,
    'PMMA-2DPAGE': None,
    'PomBase': None,
    'PptaseDB': None,
    'PRIDE': None,
    'PRINTS': None,
    'ProDom': None,
    'ProMEX': None,
    'PROSITE': None,
    'ProtClustDB': None,
    'ProteinModelPortal': None,
    'PseudoCAP': None,
    'Rat-heart-2DPAGE': None,
    'Reactome': None,
    'REBASE': None,
    'RefSeq': None,
    'REPRODUCTION-2DPAGE': None,
    'RGD': translate_RGD,
    'SGD': translate_SGD,
    'Siena-2DPAGE': None,
    'SMART': None,
    'SMR': None,
    'STRING': None,
    'SUPFAM': None,
    'SWISS-2DPAGE': None,
    'TAIR': translate_TAIR,
    'TCDB': None,
    'TIGR': None,
    'TIGRFAMs': None,
    'TubercuList': None,
    'UCD-2DPAGE': None,
    'UniGene': None,
    'UCSC': None,
    'VectorBase': None,
    'World-2DPAGE': None,
    'WormBase': translate_WormBase,
    'Xenbase': translate_Xenbase,
    'ZFIN': None,
    }


class Parser(AbstractLoader):
    """
    A parser for UniProtKB text files.

    Implements the `AbstractParser._parse` method.
    """

    def _setup(self, stream:io.TextIOWrapper) -> int:
        lines = super(Parser, self)._setup(stream)
        self._length = None
        self._id = None
        self._name_cat = None
        self.record = None
        self.db_key = None
        self._name_state = None
        self._skip_sequence = False

        def skip(line):
            return 0

        self._dispatcher = {"ID": self._parseID, "AC": self._parseAC,
                            #"DT": self._parseDT,
                            "DE": self._parseDE,
                            "GN": self._parseGN, "OX": self._parseOX,
                            "DR": self._parseDR, "KW": self._parseKW,
                            "SQ": self._parseSQ, "//": self._parseEND,
                            "OS": skip, "OG": skip, "OC": skip, "OH": skip,
                            "RN": skip, "RP": skip, "RC": skip, "RX": skip,
                            "RG": skip, "RA": skip, "RT": skip, "RL": skip,
                            "CC": skip, "PE": skip, "FT": skip,
                            "DT": skip,
                            }

        return lines

    def _cleanup(self, stream:io.TextIOWrapper) -> int:
        return super(Parser, self)._cleanup(stream)

    def _parse(self, line:str) -> int:
        if line and not self._skip_sequence:
            return self._dispatcher[line[0:2]](line)
        elif self._skip_sequence and line.startswith('//'):
            return self._parseEND(line)
        else:
            return 0

    ID_RE = re.compile(
        'ID\s+(?P<id>\w+)\s+(?P<status>Reviewed|Unreviewed);\s+(?P<length>\d+)\s+AA\.'
    )

    def _parseID(self, line:str):
        mo = Parser.ID_RE.match(line)
        self._id = mo.group('id')
        self._length = int(mo.group('length'))
        return 0

    AC_RE = re.compile('\s+(?P<accession>[A-Z][0-9][A-Z0-9]{3}[0-9]);')

    def _parseAC(self, line:str):
        accessions = Parser.AC_RE.findall(line)

        # only once, even if there are multiple AC lines:
        if self.record is None:
            # ensure a species ID has to be set later:
            #noinspection PyTypeChecker
            self.record = ProteinRecord(-1, length=self._length)
            self.db_key = DBRef(Namespace.uniprot, accessions[0])

            if self._id:
                #noinspection PyTypeChecker
                self.record.addString("identifier", self._id)

        self.record.addDBRef(DBRef(Namespace.uniprot, accessions.pop(0)))

        for acc in accessions:
            self.record.addString("accession", acc)

        return 0

#    DT_RE = re.compile(
#        'DT\s+\d{2}\-[A-Z]{3}\-\d{4}, entry version (?P<version>\d+)\s*\.'
#    )
#
#    def _parseDT(self, line:str):
#        mo = Parser.DT_RE.match(line)
#
#        if mo:
#            self.record.version = mo.group('version')
#
#        return 0

    DE_RE = re.compile(
        'DE\s+(?:(?P<category>(?:Rec|Alt|Sub)Name|Flags|Contains|Includes):)?(?:\s*(?P<subcategory>[^=]+)(?:=(?P<name>.+))?)?'
    )

    def _parseDE(self, line:str):
        mo = Parser.DE_RE.match(line)
        cat = mo.group('category')
        subcat = mo.group('subcategory')
        name = mo.group('name')

        if cat in ('Flags', 'Contains', 'Includes'):
            return 0
        elif cat:
            self._name_cat = cat

        assert subcat is not None and name is not None, line
        assert name[-1] == ';', name
        name = name[:-1]

        if subcat == "Short" and len(name) > 16 and ' ' in name:
            subcat = "Full"

        if subcat == "Full":
            name = "{}{}".format(name[0].lower(), name[1:])

            while name.startswith("uncharacterized protein ") or \
               name.startswith("putative ") or\
               name.startswith("probable "):
                if name.startswith("uncharacterized protein "):
                    name = name[24:]
                else:
                    name = name[9:]

                if ' ' not in name and len(name) < 16:
                    subcat = "Short"

            comma = name.rfind(', ')

            while comma != -1:
                name = "{} {}".format(name[comma+2:], name[:comma])
                comma = name.rfind(', ')

        if self._name_cat == 'RecName':
            if subcat == 'Full':
                self.record.name = name
            elif subcat == 'Short' and not self.record.symbol:
                self.record.symbol = name
            elif subcat == 'EC' and not self.record.symbol:
                self.record.symbol = "EC{}".format(name)

        if subcat == 'Full':
            self.record.addName(name)
        elif subcat == 'Short':
            self.record.addSymbol(name)
        elif subcat == 'EC':
            self.record.addKeyword("EC{}".format(name))
        elif subcat in ('Allergen', 'Biotech', 'CD_antigen', 'INN'):
            pass
        else:
            raise RuntimeError(
                'unknown DE subcategory field "{}"'.format(subcat)
            )

        return 0

    GN_RE = re.compile('\s+(?P<key>\w+)\s*=\s*(?P<value>[^;]+);')

    def _parseGN(self, line:str):
        if line == 'and':
            return

        for key, value in Parser.GN_RE.findall(line):
            if key == 'Name':
                if len(value) < 16 or ' ' not in value:
                    self.record.addSymbol(value)
                else:
                    self.record.addName(value)
            elif key == 'Synonyms':
                for s in value.split(','):
                    s = s.strip()

                    if len(s) < 16 or ' ' not in s:
                        self.record.addSymbol(s)
                    else:
                        self.record.addName(s)
            elif key in ('OrderedLocusNames', 'ORFNames'):
                for s in value.split(','):
                    self.record.addKeyword(s.strip())
            else:
                raise RuntimeError(
                    'unknown GN category field "{}"'.format(key)
                )

        return 0

    OX_RE = re.compile('OX\s+NCBI_TaxID\s*=\s*(?P<species>\d+);')

    def _parseOX(self, line:str):
        species = Parser.OX_RE.match(line).group('species')

        if species:
            self.record.species_id = int(species)

        return 0

    DR_RE = re.compile(
        'DR\s+(?P<namespace>[\w/\-]+)\s*;\s+(?P<accessions>.*)'
    )

    def _parseDR(self, line:str):
        mo = Parser.DR_RE.match(line)
        namespace = mo.group('namespace')

        if TRANSLATE[namespace]: # raises KeyError if unknown NSs are added
            assert mo.group('accessions')[-1] == '.', mo.group('accessions')

            for db_ref in TRANSLATE[namespace]([
                i.strip() for i in mo.group('accessions')[:-1].split(';')
            ]):
                self.record.addDBRef(db_ref)

        return 0

    KW_RE = re.compile('\s+(?P<keyword>[^;]+)(?:;|\.$)')

    def _parseKW(self, line:str):
        map(self.record.addKeyword, [
            kw for kw in Parser.KW_RE.findall(line)
            if kw != 'Complete proteome'
        ])
        return 0

    SQ_RE = re.compile(
        'SQ\s+SEQUENCE\s+(?P<length>\d+)\s+AA;\s+(?P<mass>\d+)\s+MW;\s+(?P<crc64>\w+)\s+CRC64;'
    )

    def _parseSQ(self, line:str):
        self.record.mass = int(Parser.SQ_RE.match(line).group('mass'))
        self._skip_sequence = True
        return 0

    #noinspection PyUnusedLocal
    def _parseEND(self, line:str):
        #noinspection PyTypeChecker
        self._loadRecord(self.db_key, self.record)
        self.record = None
        self.db_key = None
        self._skip_sequence = False
        self._length = None
        self._id = None
        self._name_cat = None
        return 1

class SpeedLoader(Parser):
    """
    Overrides the database loading methods to directly dump all data "as is".
    """

    def setDSN(self, dsn:str):
        """
        Set the DSN string for connecting psycopg2 to a Postgres DB.

        :param dsn: the DSN string
        """
        self._dsn = dsn

    def _setup(self, stream:io.TextIOWrapper) -> int:
        logging.debug('speedloader setup')
        lines = super(SpeedLoader, self)._setup(stream)
        self._protein_id = self.session.execute(Sequence('proteins_id_seq'))
        self._initBuffers()
        self._links = set()
        self._connect()
        self._db_key2gid_map = dict()
        self._loadExistingLinks()
        return lines

    def _initBuffers(self):
        self._proteins = io.StringIO()
        self._protein_refs = io.StringIO()
        self._protein_strings = io.StringIO()
        self._mappings = io.StringIO()

    def _loadExistingLinks(self):
        cursor = self._conn.cursor('refs')
        cursor.execute("SELECT namespace, accession, id FROM gene_refs;")

        for ns, acc, gid in cursor:
            db_key = DBRef(ns, acc)
            self._db_key2gid_map[db_key] = gid

        cursor.close()
        logging.debug('loaded %s links', len(self._db_key2gid_map))

    def _connect(self):
        import psycopg2
        self._conn = psycopg2.connect(self._dsn)

    def _flush(self):
        """
        Overrides the default `AbstractLoader._loadRecord` method.
        """
        cur = self._conn.cursor()
        stream = lambda buffer: io.StringIO(buffer.getvalue())

        try:
            cur.copy_from(stream(self._proteins), 'proteins')
            cur.copy_from(stream(self._protein_refs), 'protein_refs')
            cur.copy_from(stream(self._protein_strings), 'protein_strings')
            cur.copy_from(stream(self._mappings), 'genes2proteins')
            cur.execute("ALTER SEQUENCE proteins_id_seq RESTART WITH %s",
                (self._protein_id,))
        finally:
            cur.close()

        self._initBuffers()

    def _cleanup(self, stream:io.TextIOWrapper) -> int:
        self._flush()
        self._conn.commit()
        self._conn.close()
        return 0

    def _loadRecord(self, db_key:DBRef, record:ProteinRecord):
        """
        Overrides the default `AbstractLoader._loadRecord` method.

        :param db_key: the "primary" namespace, accession from the parsed
                       record
        :param record: a `ProteinRecord` generated from the parsed record
        """
        pid = str(self._protein_id)

        self._proteins.write('{}\t{}\t{}\t{}\n'.format(
            pid, str(record.species_id),
            '\\N' if record.length is None else record.length,
            '\\N' if record.mass is None else record.mass
        ))

        self._protein_refs.write('{}\t{}\t{}\t{}\t{}\n'.format(
            db_key.namespace, db_key.accession,
            '\\N' if record.symbol is None else record.symbol,
            '\\N' if record.name is None else record.name, pid
        ))

        for ns, acc in record.refs:
            if ns != db_key.namespace or acc != db_key.accession:
                self._protein_refs.write('{}\t{}\t\\N\t\\N\t{}\n'.format(
                    ns, acc, pid
                ))

        for cat, values in record.strings.items():
            for val in values:
                self._protein_strings.write(
                    '{}\t{}\t{}\n'.format(pid, cat, val)
                )

        gene_ids = set()

        for key in record.mappings:
            try:
                gene_ids.add(self._db_key2gid_map[key])
            except KeyError:
                pass

        for gid in gene_ids:
            self._mappings.write('{}\t{}\n'.format(gid, pid))

        self._protein_id += 1



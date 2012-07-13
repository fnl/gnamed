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
from libgnamed.loader import Record, AbstractProteinParser
from libgnamed.parsers import AbstractParser

class SpeedLoader(AbstractParser):
    # TODO
    pass


def translate_BioCyc(items:list):
    ns, acc = items[0].split(':')

    if ns == 'EcoCyc':
        yield (Namespace.ecocyc, acc)


def translate_Ensemble(items:list):
    for acc in items:
        yield (Namespace.ensemble, acc)


def translate_FlyBase(items:list):
    yield (Namespace.flybase, items[0])


def translate_GeneID(items:list):
    yield (Namespace.entrez, items[0])


def translate_HGNC(items:list):
    assert items[0].startswith('HGNC:'), items
    yield (Namespace.hgnc, items[0].split(':')[1])


def translate_MGI(items:list):
    assert items[0].startswith('MGI:'), items
    yield (Namespace.hgnc, items[0].split(':')[1])


def translate_RGD(items:list):
    yield (Namespace.rgd, items[0])


def translate_SGD(items:list):
    yield (Namespace.sgd, items[0])


def translate_TAIR(items:list):
    yield (Namespace.tair, items[0])


def translate_WormBase(items:list):
    yield (Namespace.wormbase, items[0])


def translate_Xenbase(items:list):
    yield (Namespace.xenbase, items[0])


TRANSLATE = {
    'EMBL': None,
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
    'Ensembl': translate_Ensemble,
    'EnsemblBacteria': translate_Ensemble,
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


class Parser(AbstractProteinParser):
    """
    A parser for UniProtKB text files.
    """

    def _setup(self, stream:io.TextIOWrapper):
        logging.debug("file header:\n%s", stream.readline().strip())
        self._mass = -1
        self._length = -1
        self._name_cat = None
        self.record = None
        self._name_state = None
        self._skip_sequence = False
        self._dispatcher = {"ID": self._parseID, "AC": self._parseAC,
                            "DT": self._parseDT, "DE": self._parseDE,
                            "GN": self._parseGN, "OX": self._parseOX,
                            "DR": self._parseDR, "KW": self._parseKW,
                            "SQ": self._parseSQ, "//": self._parseEND}

        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        return 0

    def _parse(self, line:str):
        if line and not self._skip_sequence:
            line_type = line[0:2]

            if line_type in self._dispatcher:
                self._dispatcher[line_type](line[5:].strip())

                if line_type == 'SQ':
                    self._skip_sequence = True

            return 0
        elif self._skip_sequence and line.startswith('//'):
            self._skip_sequence = False
            return 1
        else:
            return 0

    ID_RE = re.compile(
        '^\w+\s+(?P<status>Reviewed|Unreviewed);\s+(?P<length>\d+)\s+AA\.$'
    )

    def _parseID(self, line:str):
        self._length = int(Parser.ID_RE.search(line).group('length'))

    AC_RE = re.compile('\s*(?P<accession>[A-Z][0-9][A-Z0-9]{3}[0-9])\s*;')

    def _parseAC(self, line:str):
        accessions = Parser.AC_RE.findall(line)

        if self.record is None:
            # ensure a species ID has to be set later:
            self.record = Record(Namespace.uniprot, accessions[0], -1)
            # ensure a version has to be set later:
            self.record.version = lambda: 'undefined'
            start = 1
        else:
            start = 0

        self.record.links.update(
            (Namespace.uniprot, acc) for acc in accessions[start:]
        )

    DT_RE = re.compile(
        '^\s*\d{2}\-[A-Z]{3}\-\d{4}, entry version (?P<version>\d+)\s*\.\s*$'
    )

    def _parseDT(self, line:str):
        mo = Parser.DT_RE.search(line)

        if mo:
            self.record.version = mo.group('version')

    DE_RE = re.compile(
        '^(?:(?P<category>(?:Rec|Alt|Sub)Name|Flags|Contains|Includes):)?(?:\s*(?P<subcategory>[^=]+)(?:=(?P<name>.+))?)?$'
    )

    def _parseDE(self, line:str):
        mo = Parser.DE_RE.search(line)
        cat = mo.group('category')
        subcat = mo.group('subcategory')
        name = mo.group('name')

        if cat in ('Flags', 'Contains', 'Includes'):
            return
        elif cat:
            self._name_cat = cat

        assert subcat is not None and name is not None, line

        if self._name_cat == 'RecName':
            if subcat == 'Full':
                self.record.name = name[:-1]
            elif subcat == 'Short' and not self.record.symbol:
                self.record.symbol = name[:-1]
            elif subcat == 'EC' and not self.record.symbol:
                self.record.symbol = name[:-1]

        if subcat == 'Short':
            self.record.symbols.add(name[:-1])
        elif subcat == 'EC':
            self.record.symbols.add(name[:-1])
        elif subcat == 'Full':
            self.record.names.add(name[:-1])
        elif subcat in ('Allergen', 'Biotech', 'CD_antigen', 'INN'):
            pass
        else:
            raise RuntimeError(
                'unknown DE subcategory field "{}"'.format(subcat)
            )

    GN_RE = re.compile('\s*(?P<key>\w+)\s*=\s*(?P<value>[^;]+);')

    def _parseGN(self, line:str):
        if line == 'and':
            return

        if not hasattr(self.record, 'gene_symbols'):
            self.record.gene_symbols = set()

        for key, value in Parser.GN_RE.findall(line):
            if key == 'Name':
                self.record.gene_symbols.add(value)
            elif key in ('Synonyms', 'OrderedLocusNames', 'ORFNames'):
                self.record.gene_symbols.update(
                    s.strip() for s in key.split(',')
                )
            else:
                raise RuntimeError(
                    'unknown GN category field "{}"'.format(key)
                )

    OX_RE = re.compile('^\s*NCBI_TaxID\s*=\s*(?P<species>\d+)\s*;\s*$')

    def _parseOX(self, line:str):
        species = Parser.OX_RE.search(line).group('species')

        if species:
            self.record.species_id = int(species)

    DR_RE = re.compile(
        '^\s*(?P<namespace>[\w/\-]+)\s*;\s+(?P<accessions>.*)$'
    )

    def _parseDR(self, line:str):
        mo = Parser.DR_RE.search(line)
        namespace = mo.group('namespace')

        if TRANSLATE[namespace]:
            self.record.links.update(
                TRANSLATE[namespace]([
                i.strip() for i in mo.group('accessions')[:-1].split(';')
                ])
            )

    KW_RE = re.compile('\s*(?P<keyword>[^;]+);')

    def _parseKW(self, line:str):
        self.record.keywords.update(Parser.KW_RE.findall(line))

    SQ_RE = re.compile(
        '^\s*SEQUENCE\s+(?P<length>\d+)\s+AA;\s+(?P<mass>\d+)\s+MW;\s+(?P<crc64>\w+)\s+CRC64;\s*$'
    )

    def _parseSQ(self, line:str):
        self._mass = int(Parser.SQ_RE.search(line).group('mass'))

    #noinspection PyUnusedLocal
    def _parseEND(self, line:str):
        #noinspection PyTypeChecker
        self.loadRecord(self.record, mass=self._mass, length=self._length)
        self._mass = None
        self._length = None
        self._record = None
        self._name_cat = None

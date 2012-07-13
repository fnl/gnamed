"""
.. py:module:: libgnamed.parsers.hgnc
   :synopsis: a HGNC (genenames.org) parser

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import io
import logging

from collections import namedtuple
from shlex import shlex

from libgnamed.constants import Species, Namespace
from libgnamed.loader import Record, AbstractGeneParser

Line = namedtuple('Line', [
    'id', 'symbol', 'name',
    'previous_symbols', 'previous_names', 'synonyms', 'name_synonyms',
    'location', 'pmids',
    'gene_family_symbols', 'gene_family_names',
    Namespace.entrez, Namespace.ensemble, Namespace.mgd,
    Namespace.uniprot, Namespace.rgd
])

LINKS = [Namespace.entrez, Namespace.ensemble, Namespace.mgd,
         Namespace.uniprot, Namespace.rgd]
FIX_ACCESSION = frozenset([Namespace.mgd, Namespace.rgd])

class Parser(AbstractGeneParser):
    """
    A parser for HGNC (genenames.org) records.
    """

    def _setup(self, stream:io.TextIOWrapper):
        logging.debug("file header:\n%s", stream.readline().strip())
        return 1

    def _parse(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        assert len(items) > 1, line

        for idx in range(len(items)):
            if items[idx] == '-':
                items[idx] = ''

        while len(items) < 16:
            items.append('')

        row = Line._make(items)
        record = Record(Namespace.hgnc, row.id, Species.human,
                        symbol=row.symbol, name=row.name)

        # link DB references
        for ns in LINKS:
            acc = getattr(row, ns)

            if acc:
                if ns in FIX_ACCESSION:
                    acc = acc[acc.find(":") + 1:]

                record.links.add((ns, acc))

        # parse symbol strings
        for field in (row.previous_symbols, row.synonyms):
            record.symbols.update(Parser._parseCD(field))

        # parse name strings
        for field in (row.previous_names, row.name_synonyms):
            record.names.update(Parser._parseQCD(field))

        # parse keywords strings
        record.keywords.update(Parser._parseCD(row.gene_family_symbols))

        for name in Parser._parseQCD(row.gene_family_names):
            for subname in name.split(' / '):
                for subsubname in subname.split(' : '):
                    subsubname = subsubname.strip()

                    if subsubname.lower() not in ('other', '"other"'):
                        record.keywords.add(subsubname)

        self.loadRecord(record, location=row.location)
        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        return 0

    @staticmethod
    def _parseQCD(content:str) -> shlex:
        parser = shlex(content, posix=True)
        parser.whitespace += ','
        parser.whitespace_split = True

        for value in parser:
            value = value.strip()

            if value:
                yield value

    @staticmethod
    def _parseCD(content:str) -> shlex:
        for value in content.split(','):
            value = value.strip()

            if value:
                yield value


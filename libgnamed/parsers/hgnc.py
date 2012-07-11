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

from libgnamed.loader import Namespace, Record, Species, AbstractGeneParser

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
            record.symbols.update(
                sym.strip() for sym in field.split(',') if sym.strip()
            )

        # parse name strings
        for field in (row.previous_names, row.name_synonyms):
            items = shlex(field, posix=True)
            items.whitespace += ','
            items.whitespace_split = True
            record.names.update(n.strip() for n in items if n.strip())

        self.loadRecord(record, location=row.location)
        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        return 0

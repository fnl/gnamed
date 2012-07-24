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
from libgnamed.loader import GeneRecord, AbstractLoader, DBRef

Line = namedtuple('Line', [
    'id', 'symbol', 'name',
    'previous_symbols', 'previous_names', 'synonyms', 'name_synonyms',
    'location', 'pmids',
    'gene_family_symbols', 'gene_family_names',
    Namespace.entrez, 'Namespace_ensemble', Namespace.mgd,
    Namespace.uniprot, Namespace.rgd
])

DB_REFS = [Namespace.entrez,
         Namespace.uniprot]
FIX_ACCESSION = frozenset({Namespace.mgd, Namespace.rgd})

# Mapping of references to other DBs that are no longer correct to their
# actual, new values
WRONG_DB_REFS = {
    DBRef(Namespace.entrez, '276721'): DBRef(Namespace.entrez, '100422411'),
    DBRef(Namespace.entrez, '446205'): DBRef(Namespace.entrez, '646086'),
    DBRef(Namespace.entrez, '100033412'): DBRef(Namespace.entrez, '100420926'),
    #DBRef(Namespace.entrez, ''): DBRef(Namespace.entrez, ''),
    }

class Parser(AbstractLoader):
    """
    A parser for HGNC (genenames.org) records.

    Implements the `AbstractParser._parse` method.
    """

    def _setup(self, stream:io.TextIOWrapper):
        lines = super(Parser, self)._setup(stream)
        logging.debug("file header:\n%s", stream.readline().strip())
        return lines + 1

    def _parse(self, line:str):
        items = [i.strip() for i in line.split('\t')]
        assert len(items) > 1, line

        for idx in range(len(items)):
            if items[idx] == '-':
                items[idx] = ''

        while len(items) < 16:
            items.append('')

        row = Line._make(items)
        record = GeneRecord(Species.human, symbol=row.symbol, name=row.name,
                            location=row.location if row.location else None)
        record.addDBRef(DBRef(Namespace.hgnc, row.id))

        # link DB references
        for ns in DB_REFS:
            acc = getattr(row, ns)

            if acc:
                if ns in FIX_ACCESSION:
                    acc = acc[acc.find(":") + 1:]

                ref = DBRef(ns, acc)

                if ref in WRONG_DB_REFS:
                    new_ref = WRONG_DB_REFS[ref]
                    logging.info('correcting outdated ref %s->%s',
                                 '{}:{}'.format(*ref),
                                 '{}:{}'.format(*new_ref))
                    ref = new_ref

                record.addDBRef(ref)

        # parse symbol strings
        for field in (row.previous_symbols, row.synonyms):
            if field:
                map(record.addSymbol, Parser._parseCD(field))

        # parse name strings
        for field in (row.previous_names, row.name_synonyms):
            if field:
                map(record.addName, Parser._parseQCD(field))

        # parse keywords strings
        if row.gene_family_symbols:
            map(record.addKeyword, Parser._parseCD(row.gene_family_symbols))

        for name in Parser._parseQCD(row.gene_family_names):
            for subname in name.split(' / '):
                for subsubname in subname.split(' : '):
                    subsubname = subsubname.strip()

                    if subsubname.lower() not in ('other', '"other"'):
                        record.addKeyword(subsubname)

        self._loadRecord(DBRef(Namespace.hgnc, row.id), record)
        return 1

    def _cleanup(self, file:io.TextIOWrapper):
        records = super(Parser, self)._cleanup(file)
        return records

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


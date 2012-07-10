#!/usr/bin/env python3
"""
GNU Public License v3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

Copyright 2011, Florian Leitner. All rights reserved.
"""
import logging
import os
import sys

from collections import namedtuple, Callable
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, IntegrityError

from loader import \
    argparser, dereference, Namespace, NAMESPACES, loadGeneRecord, Record, setup
from orm import Session
from progress_bar import initBarForInfile

__author__ = "Florian Leitner"
__version__ = "0.1"
synopsis = "load Entrez Gene data into a gnamed DB"

Line = namedtuple('Line', [
    'species_id', 'id',
    'symbol', 'locus_tag', 'synonyms', 'dbxrefs', 'chromosome',
    'map_location', 'name', 'type_of_gene', 'nomenclature_symbol',
    'nomenclature_name', 'nomenclature_status', 'other_designations',
    'modification_date'
])
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

LOOKUP = dict((ns, xref) for xref, ns in TRANSLATE.items())

def addNsAcc(row:Line, ns:str, recordAddFun:Callable):
    acc = getattr(row, ns)

    if acc and acc != '-':
        recordAddFun(ns, acc)

def isGeneSymbol(sym:str) -> bool:
    return len(sym) < 65 and " " not in sym

def main(file:str, links:list, encoding:str=None) -> int:
    """
    :param file: path to the file to import
    :param links: list of namespaces to links to (see loader.Namespaces)
    :param encoding: encoding of that file (default: system encoding)
    :return: 0 if successful, 1 otherwise
    """
    logging.info('reading %s (%s)', file, encoding)
    session = Session(autoflush=False)
    references = [ns for ns in NAMESPACES if ns not in (
        Namespace.entrez,
    ) and ns not in links]
    stream = open(file, encoding=encoding)
    progress_bar = None

    if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
        logging.debug("file header:\n%s", stream.readline().strip())
    else:
        progress_bar = initBarForInfile(file)
        stream.readline() # skip header line

    line = stream.readline().strip()
    count = 1

    while line:
        try:
            count += 1

            if progress_bar is not None and count % 100 == 0:
                #noinspection PyCallingNonCallable
                progress_bar(stream.tell())

            #noinspection PyTypeChecker
            items = [i.strip() for i in line.split('\t')]

            if items[2] == 'NEWENTRY':
                line = stream.readline().strip()
                continue

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
            assert not row.symbol or len(row.symbol) < 65, \
                '{}:{} has an illegal symbol="{}"'.format(
                    Namespace.entrez, row.id, row.symbol
                )
            record = Record(Namespace.entrez, row.id, row.species_id,
                            symbol=row.symbol, name=row.name)

            # separate existing DB links and new DB references
            if row.dbxrefs:
                dbxrefs = dict(
                    xref.split(':') for xref in row.dbxrefs.split('|')
                )

                for collection, fun in [
                    (links, record.addLink), (references, record.addReference)
                ]:
                    for ns in collection:
                        if LOOKUP[ns] in dbxrefs:
                            fun(ns, dbxrefs[LOOKUP[ns]])

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

            loadGeneRecord(session, record, chromosome=row.chromosome)
            line = stream.readline().strip()
        except Exception as e:
            if progress_bar is not None:
                del progress_bar

            session.rollback()
            logging.warning("%s while parsing line %s:\n%s",
                          e.__class__.__name__, count, line.strip())

            if logging.getLogger().getEffectiveLevel() < logging.INFO:
                logging.exception(e)
            else:
                logging.fatal(str(e).strip())

            return 1

    if progress_bar is not None:
        del progress_bar

    session.commit()
    logging.info("processed %s records", count - 1)
    session.close()
    stream.close()
    return 0

if __name__ == '__main__':
    parser = argparser(synopsis, __version__)

    parser.add_argument(
        'file', metavar='FILE',
        help="path to the gene_info file to load"
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        parser.error('file "{}" does not exist'.format(args.file))

    db_url = URL(args.driver, username=args.username, password=args.password,
                 host=args.host, port=args.port, database=args.database)

    try:
        setup(db_url, args.loglevel, args.logfile)
    except OperationalError as oe:
        parser.error(str(oe.orig).strip())

    try:
        sys.exit(main(args.file, list(dereference(args)),
                      encoding=args.encoding))
    except IntegrityError as ie:
        if args.loglevel < logging.INFO:
            logging.exception(ie)
        else:
            logging.fatal(str(ie.orig).strip())

        sys.exit(1)

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
from shlex import shlex
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, IntegrityError

from loader import\
    argparser, dereference, Namespace, NAMESPACES, loadGeneRecord, Record, Species, setup
from orm import Session
from progress_bar import initBarForInfile

__author__ = "Florian Leitner"
__version__ = "0.1"
synopsis = "load HGNC data into a gnamed DB"

Line = namedtuple('Line',
    [
        'hgnc',
        'symbol', 'name', 'previous_symbols', 'previous_names',
        'synonyms', 'name_synonyms',
        'location', 'pmids',
        'gene_family_symbols', 'gene_family_names',
        Namespace.entrez, Namespace.ensemble, Namespace.mgd,
        Namespace.uniprot, Namespace.rgd
    ])

def addNsAcc(row:Line, ns:str, recordAddFun:Callable):
    acc = getattr(row, ns)

    if ns in (Namespace.mgd, Namespace.rgd):
        idx = acc.find(":") + 1
        if idx: acc = acc[idx:]

    if acc and acc != '-':
        recordAddFun(ns, acc)

def main(file:str, links:list, encoding:str=None) -> int:
    """
    :param file: path to the file to import
    :param links: list of namespaces to links to (see loader.Namespaces)
    :param encoding: encoding of that file (default: system encoding)
    :return: 0 if successful, 1 otherwise
    """
    logging.info('reading %s (%s)', file, encoding)
    session = Session(autoflush=False)
    references = [ns for ns in NAMESPACES if ns in (
        Namespace.ensemble, Namespace.entrez, Namespace.uniprot,
        Namespace.mgd, Namespace.rgd
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

            if progress_bar is not None and count % 10 == 0:
                #noinspection PyCallingNonCallable
                progress_bar(stream.tell())

            #noinspection PyTypeChecker
            items = [i.strip() for i in line.split('\t')]
            assert len(items) > 1, line

            while len(items) < 16:
                items.append('')

            row = Line._make(items)
            record = Record(Namespace.hgnc, row.hgnc, Species.human,
                            symbol=row.symbol, name=row.name)

            # separate existing DB links and new DB references
            for collection, fun in [
                (links, record.addLink), (references, record.addReference)
            ]:
                for ns in collection:
                    addNsAcc(row, ns, fun)

            # parsed symbol strings
            for field in (row.previous_symbols, row.synonyms):
                record.symbols.update(
                    sym.strip() for sym in field.split(',') if sym.strip()
                )

            # parsed name strings
            for field in (row.previous_names, row.name_synonyms):
                items = shlex(field, posix=True)
                items.whitespace += ','
                items.whitespace_split = True
                record.names.update(n.strip() for n in items if n.strip())

            loadGeneRecord(session, record, location=row.location)
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
        help="path to the hgnc.csv file to load"
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

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

from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, IntegrityError

from loader import setup, argparser
from orm import Session, Species
from progress_bar import initBarForInfile

__author__ = 'Florian Leitner'
__version__ = '0.1'
synopsis = "setup a gnamed DB schema and load the NCBI Taxonomy data into it"

def main(file:str, encoding:str=None) -> int:
    """
    :param file: path to the file to import
    :param encoding: encoding of that file (default: system encoding)
    :return: 0 if successful, 1 otherwise
    """
    logging.info('reading %s (%s)', file, encoding)
    session = Session(autoflush=True)
    stream = open(file, encoding=encoding)
    progress_bar = None

    if logging.getLogger().getEffectiveLevel() > logging.DEBUG:
        progress_bar = initBarForInfile(file)

    current_id = None
    record = None
    line = stream.readline().strip()
    line_count = 1
    num_records = 0

    while line:
        try:
            line_count += 1

            if progress_bar is not None and line_count % 100 == 0:
                #noinspection PyCallingNonCallable
                progress_bar(stream.tell())

            #noinspection PyTypeChecker
            items = [i.strip() for i in line.split('|')]
            assert len(items) == 5, line

            if items[0] != current_id:
                if record:
                    num_records += 1
                    logging.debug("storing %s", record)
                    session.add(record)

                    if num_records % 1000 == 0:
                        session.flush()

                record = Species(int(items[0]))
                current_id = items[0]

            if items[3] == 'common name':
                record.common_name = items[1]
            elif items[3] == 'scientific name':
                record.scientific_name = items[1]
            elif items[3] == 'acronym':
                record.acronym = items[1]
            elif items[3] == 'genbank common name' and not record.common_name:
                record.common_name = items[1]
            elif items[3] == 'genbank acronym'  and not record.acronym:
                record.acronym = items[1]

            line = stream.readline().strip()
        except Exception as e:
            if progress_bar is not None:
                del progress_bar

            session.rollback()
            logging.warning("%s while parsing\n%s",
                            e.__class__.__name__, line.strip())
            logging.exception(e)
            return 1

    if progress_bar is not None:
        del progress_bar

    logging.info("added %s species records", num_records)
    session.commit()
    session.close()
    return 0

if __name__ == '__main__':
    parser = argparser(synopsis, __version__)

    parser.add_argument(
        'file', metavar='FILE',
        help="path to the names.dmp file to load"
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
        sys.exit(main(args.file, encoding=args.encoding))
    except IntegrityError as ie:
        if args.loglevel < logging.INFO:
            logging.exception(ie)
        else:
            logging.fatal(str(ie.orig).strip())

        sys.exit(1)

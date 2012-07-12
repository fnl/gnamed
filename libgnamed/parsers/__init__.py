"""
.. py:module:: libgnamed.parsers
   :synopsis: a library of parsers for the gnamed gene/protein name repo

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import sys
import io
from libgnamed.orm import Session
from libgnamed.progress_bar import initBarForInfile

class AbstractParser:
    """
    An abstract parser implementation that opens file streams, handles DB
    sesssions (creating, flushing, committing) and creates a
    `libgnamed.progress_bar` given the log-level.
    """

    def __init__(self, *files:str, encoding:str=sys.getdefaultencoding()):
        """
        :param files: any number of files (pathnames) to load
        :param encoding: the character encoding used by these files
        """
        self.session = None
        self.db_objects = None
        self.files = files
        self.encoding = encoding
        self.record = None
        self.current_id = None

    def parse(self):
        """
        Parse all relevant files and commit the added records to the DB.

        Manages DB session state/handling.
        """
        self.session = Session(autoflush=False)

        for file in self.files:
            logging.info('parsing %s (%s)', file, self.encoding)
            stream = open(file, encoding=self.encoding)
            progress_bar = None

            if logging.getLogger().getEffectiveLevel() > logging.DEBUG:
                progress_bar = initBarForInfile(file)

            self.record = None
            self.current_id = None
            self.db_objects = {}
            line_count = self._setup(stream)

            line = stream.readline().strip()
            line_count += 1
            num_records = 0

            while line:
                try:
                    if progress_bar is not None and line_count % 100 == 0:
                        #noinspection PyCallingNonCallable
                        progress_bar(stream.tell())

                    num_records += self._parse(line)

                    if num_records % 10000 == 0:
                        self._flush()

                    line = stream.readline().strip()
                    line_count += 1
                except Exception as e:
                    if progress_bar is not None:
                        del progress_bar

                    self.session.rollback()
                    logging.warn("%s while parsing line %s:\n%s",
                                 e.__class__.__name__, line_count,
                                 line.strip())

                    if logging.getLogger().getEffectiveLevel() <= logging.INFO:
                        logging.exception(e)
                    else:
                        logging.fatal(str(e).strip())

                    return

            num_records += self._cleanup(stream)

            if progress_bar is not None:
                del progress_bar

            try:
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                logging.warn("%s while committing the parsed data",
                             e.__class__.__name__)

                if logging.getLogger().getEffectiveLevel() <= logging.INFO:
                    logging.exception(e)
                else:
                    logging.error(str(e).strip())
            else:
                logging.info("added %s records from %s", num_records, file)

        try:
            self.session.close()
        except Exception as e:
            logging.warn("%s while closing the session", e.__class__.__name__)

            if logging.getLogger().getEffectiveLevel() <= logging.INFO:
                logging.exception(e)
            else:
                logging.fatal(str(e).strip())
        finally:
            self.session = None

    def _setup(self, stream:io.TextIOWrapper):
        """
        Setup the virgin stream and return the line count into the stream after
        setup.
        """
        return 0

    def _parse(self, line:str):
        """
        Parse a particular line and return the number of processed records.
        """
        raise NotImplementedError('abstract')

    def _flush(self):
        """
        Write currently held data into the DB to free some RAM.
        """
        self.db_objects = {}
        self.session.flush()

    def _cleanup(self, stream:io.TextIOWrapper):
        """
        Clean up the stream and dangling records and return the number of
        processed records.
        """
        return 0

#class Parser(AbstractParser):
#
#    def _setup(self, stream:io.TextIOWrapper):
#        return 0 # default: no lines have been consumed
#
#    def _parse(self, line:str):
#        #self.loadRecord(record, ...)
#        return 0 # default: no record has been added
#
#    def _flush(self):
#        super(Parser, self)._flush()
#
#    def _cleanup(self, stream:io.TextIOWrapper):
#        return 0 # default: no record has been added

"""
.. py:module:: libgnamed.parsers.taxa
   :synopsis: A parser for the NCBI Taxonom names.dmp file

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import io

from libgnamed.orm import Species
from libgnamed.parsers import AbstractParser

class Parser(AbstractParser):
    """
    A parser for NCBI Taxonomy name records.
    """

    def _setup(self, file:io.TextIOWrapper):
        return 0

    def _parse(self, line:str):
        added_records = 0
        items = [i.strip() for i in line.split('|')]

        assert len(items) == 5, line

        if items[0] != self.current_id:
            if self.record:
                added_records = 1
                logging.debug("storing %s", self.record)
                self.session.add(self.record)

            self.record = Species(int(items[0]))
            self.current_id = items[0]

        if items[3] == 'common name' and not self.record.common_name:
            self.record.common_name = items[1]
        elif items[3] == 'scientific name' and not self.record.scientific_name:
            self.record.scientific_name = items[1]
        elif items[3] == 'acronym' and not self.record.acronym:
            self.record.acronym = items[1]
        elif items[3] == 'genbank common name' and not self.record.common_name:
            self.record.common_name = items[1]
        elif items[3] == 'genbank acronym'  and not self.record.acronym:
            self.record.acronym = items[1]

        return added_records

    def _cleanup(self, file:io.TextIOWrapper):
        if self.record:
            self.session.add(self.record)
            return 1
        else:
            return 0

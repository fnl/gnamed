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

__author__ = "Florian Leitner"
__version__ = "0.0"
synopsis = "download raw database files"

import logging
import os
import re
import sys
from urllib.request import urlopen, urlretrieve

# {
#   db-key: {
#     'url': base-url,
#     'resources': [(remote-path, local-file-name, remote-encoding), ...],
#     'description': db-description
#   }, ...
# }
DATABASES = {
    'taxonomy': {
        'url': 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/',
        'resources': [('taxdump.tar.gz', 'taxdump.tar.gz', None)],
        'description': "NCBI Taxonomy database",
    },
    'entrez': {
        'url': 'ftp://ftp.ncbi.nih.gov/gene/DATA/',
        'resources': [('gene_info.gz', 'gene_info.gz', None)],
        'description': "NCBI Entrez Gene information file",
    },
    'hgnc': {
        # see http://www.genenames.org/cgi-bin/hgnc_downloads.cgi for more info
        'url': 'http://www.genenames.org/cgi-bin/hgnc_downloads.cgi?',
        'resources': [('title=HGNC%20output%20data&col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_prev_sym&col=gd_prev_name&col=gd_aliases&col=gd_name_aliases&col=gd_pub_chrom_map&col=gd_pubmed_ids&col=gd_gene_fam_name&col=gd_gene_fam_pagename&col=gd_pub_eg_id&col=gd_pub_ensembl_id&col=gd_mgd_id&col=md_prot_id&col=md_rgd_id&status=Approved&status_opt=2&where=&order_by=&format=text&limit=&submit=submit&.cgifields=&.cgifields=status&.cgifields=chr&.cgifields=hgnc_dbtag', 'hgnc.csv', 'ISO-8859-1')],
        'description':
            "Human Genome Nomenclature Consoritum (genenames.org)",
    },
}

def main(*databases:str, directory:str=None,
         encoding:str=sys.getdefaultencoding()) -> int:
    """
    :param databases: databases to download
    :param directory: target directory to store the downloaded files
    :param encoding: encoding to use for output files
    """
    if not directory:
        directory = os.getcwd()

    for db in databases:
        logging.info('downloading files for "%s"', db)
        url = DATABASES[db]['url']

        for path, filename, remote_enc in DATABASES[db]['resources']:
            logging.info("streaming %s (%s)", filename, encoding)
            logging.debug("connecting to %s%s", url, path)

            if remote_enc is not None:
                stream = urlopen(url + path)
                info = stream.info()

                if 'content-type' in info and \
                   'charset' in info['content-type']:
                    mo = re.search('charset\s*=\s*(.*?)\s*$',
                                   info['content-type'])

                    if remote_enc != mo.group(1):
                        remote_enc = mo.group(1)
                        logging.warn("%s encoding is %s", url + path, remote_enc)

                output = open(os.path.join(directory, filename), mode='w',
                              encoding=encoding)

                for data in stream:
                    output.write(data.decode(remote_enc))

                output.close()
                stream.close()
            else:
                urlretrieve(url + path, os.path.join(directory, filename))

    return 0

if __name__ == '__main__':
    from argparse import ArgumentParser
    usage = "%(prog)s [options] <db-key>..."

    parser = ArgumentParser(
        usage=usage, description=synopsis,
        prog=os.path.basename(sys.argv[0]),
        epilog="version " + __version__
    )

    parser.set_defaults(loglevel=logging.WARNING)

    parser.add_argument(
        'databases', metavar='db-key', nargs='*',
        help="key name of a database to download"
    )
    parser.add_argument(
        '-l', '--list', action='store_true',
        help="list db keys that can be downloaded and exit"
    )
    parser.add_argument(
        '-d', '--dir', metavar="DIR", action='store',
        help="store files to specified directory [CWD]"
    )
    parser.add_argument(
        '-e', '--enc', action='store', metavar="ENC",
        default=sys.getdefaultencoding(),
        help="write files using specified encoding [%(default)s]"
    )
    parser.add_argument(
        '--error', action='store_const', const=logging.ERROR,
        dest='loglevel', help="set log level error [warn]"
    )
    parser.add_argument(
        '--info', action='store_const', const=logging.INFO,
        dest='loglevel', help="set log level info [warn]"
    )
    parser.add_argument(
        '--debug', action='store_const', const=logging.DEBUG,
        dest='loglevel', help="set log level debug [warn]"
    )
    parser.add_argument(
        '--logfile', metavar="FILE", help="log to file, not STDERR"
    )

    args = parser.parse_args()

    if (args.list):
        print("DB-KEY    DESCRIPTION")
        print("all       download all DBs")

        for name in DATABASES:
            print("{:<10}{}".format(name, DATABASES[name]['description']))

        sys.exit(0)

    if (not args.databases):
        parser.error('no database keys specified')

    if ('all' in args.databases):
        args.databases = DATABASES.keys()
    else:
        for db in args.databases:
            if db not in DATABASES:
                parser.error('no db for key="{}" (see --list)'.format(db))

    logging.basicConfig(
        filename=args.logfile, level=args.loglevel,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    sys.exit(main(*args.databases, directory=args.dir, encoding=args.enc))


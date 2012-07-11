"""
.. py:module:: libgnamed.fetcher
   :synopsis: download repository files

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import logging
import re
import sys
from urllib.request import urlopen, urlretrieve
import os

REPOSITORIES = {
    'taxa': {
        'url': 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/',
        'resources': [('taxdump.tar.gz', 'taxdump.tar.gz', None)],
        'description': "NCBI Taxonomy database dump",
        },
    'entrez': {
        'url': 'ftp://ftp.ncbi.nih.gov/gene/DATA/',
        'resources': [('gene_info.gz', 'gene_info.gz', None)],
        'description': "NCBI Entrez Gene gene_info file",
        },
    'uniprot': {
        'url': 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/'
        ,
        'resources': [
            ('uniprot_sprot.dat.gz', 'uniprot_sprot.dat.gz', None),
            ('uniprot_trembl.dat.gz', 'uniprot_trembl.dat.gz', None)
        ],
        'description': "UniProtKB TrEMBL/Swiss-Prot text files",
        },
    'hgnc': {
        # see http://www.genenames.org/cgi-bin/hgnc_downloads.cgi for more info
        'url': 'http://www.genenames.org/cgi-bin/hgnc_downloads.cgi?',
        'resources': [(
            'title=HGNC%20output%20data&col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_prev_sym&col=gd_prev_name&col=gd_aliases&col=gd_name_aliases&col=gd_pub_chrom_map&col=gd_pubmed_ids&col=gd_gene_fam_name&col=gd_gene_fam_pagename&col=gd_pub_eg_id&col=gd_pub_ensembl_id&col=gd_mgd_id&col=md_prot_id&col=md_rgd_id&status=Approved&status_opt=2&where=&order_by=&format=text&limit=&submit=submit&.cgifields=&.cgifields=status&.cgifields=chr&.cgifields=hgnc_dbtag'
            , 'hgnc.csv', 'ISO-8859-1')],
        'description': "Human Genome Nomenclature Consortium (genenames.org)",
        },
    }

_LOGGER = logging.getLogger("libgnamed.fetcher")

def retrieve(*repo_keys:str, directory:str=os.getcwd(),
             encoding:str=sys.getdefaultencoding()):
    """
    :param repo_keys: keys of the repositories to download
    :param directory: target directory to store the downloaded files
    :param encoding: encoding to use for text files
    """
    for db in repo_keys:
        logging.info('downloading files for "%s"', db)
        repo = REPOSITORIES[db]
        url = repo['url']

        for path, filename, remote_enc in repo['resources']:
            logging.info("streaming %s (%s) to %s",
                         filename, encoding, directory)
            logging.debug("connecting to %s%s", url, path)

            if remote_enc is not None:
                stream = urlopen(url + path)
                info = stream.info()

                if 'content-type' in info and\
                   'charset' in info['content-type']:
                    mo = re.search('charset\s*=\s*(.*?)\s*$',
                                   info['content-type'])

                    if remote_enc != mo.group(1):
                        remote_enc = mo.group(1)
                        logging.warn("%s encoding is %s",
                                     url + path, remote_enc)

                output = open(os.path.join(directory, filename), mode='w',
                              encoding=encoding)

                for data in stream:
                    output.write(data.decode(remote_enc))

                output.close()
                stream.close()
            else:
                urlretrieve(url + path, os.path.join(directory, filename))

            print(os.path.join(directory, filename), file=sys.stdout)

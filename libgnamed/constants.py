"""
.. py:module:: constants
   :synopsis: all constants used by gnamed in one place

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""

REPOSITORIES = {
    'taxa': {
        'url': 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/',
        'resources': [('taxdump.tar.gz', 'taxdump.tar.gz', None)],
        'description': "NCBI Taxonomy database dump (nodes.dmp, names.dmp)",
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

class Namespace:
    # general DBs
    ensemble = 'ens'
    entrez = 'gi'
    uniprot = 'uni'
    # organism-specific DBs
    hgnc = 'hgnc' # human
    mgd = 'mgi' # mouse
    rgd = 'rgd' # rat
    flybase = 'fly' # fly
    sgd = 'sgd' # yeast
    tair = 'tair' # cress
    ecocyc = 'eco' # e.coli
    wormbase = 'wb' # nematode
    xenbase = 'xb' # frog


NAMESPACES = frozenset({
    Namespace.ensemble,
    Namespace.entrez,
    Namespace.uniprot,
    Namespace.hgnc,
    Namespace.mgd,
    Namespace.rgd,
    Namespace.flybase,
    Namespace.sgd,
    Namespace.tair,
    Namespace.ecocyc,
    Namespace.wormbase,
    Namespace.xenbase,
    })


GENE_SPACES = frozenset({
    Namespace.ensemble,
    Namespace.entrez,
    Namespace.hgnc,
    Namespace.mgd,
    Namespace.rgd,
    Namespace.flybase,
    Namespace.sgd,
    Namespace.tair,
    Namespace.ecocyc,
    Namespace.wormbase,
    Namespace.xenbase,
    })

PROTEIN_SPACES = frozenset({
    Namespace.uniprot,
    })


class Species:
    human = 9606
    mouse = 10090
    rat = 10116
    fly = 7227
    yeast = 4932
    cress = 3702
    e_coli = 562
    nematode = 6239
    frog = 8355


SPECIES = frozenset({
    Species.human,
    Species.mouse,
    Species.rat,
    Species.fly,
    Species.yeast,
    Species.cress,
    Species.e_coli,
    Species.nematode,
    Species.frog,
    })

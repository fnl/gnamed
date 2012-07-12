Synopsis
========

A script to download gene/protein name records, bootstrap a database to store
them, and load the gene/protein names into that datastore, unifying the names
across multiple repositories into single, species-specific gene and protein
records. The datastore differentiates between names and symbols. The main
("official") name and symbol for each originating repository is retained.

Entity Relationship Model
=========================

::

          [Protein] <-> [Database] <-> [Gene]
            ^   |                       |  ^
            |    ---------v     v--------  |
  [Name,Symbol,Keywords] [Species] [Name,Symbol,Keywords]

Species (species)
  *id:INT, acronym:VARCHAR(64), common_name:TEXT, scientific_name:TEXT

Database (databases)
  *namespace:VARCHAR(8), *accession:VARCHAR(64), version:VARCHAR(16),
  symbol:VARCHAR(64), name:TEXT

Protein (proteins)
  *id:BIGINT, species_id:FK_Species, mass:INT, length:INT

Gene (genes)
  *id:BIGINT, species_id:FK_Species, chromosome:VARCHAR(32),
  location:VARCHAR(64)

Database2Protein, Database2Gene
  *namespace:FK_Database, *accession:FK_Database,
  *protein_id/gene_id:FK_Protein/FK_Gene,

GeneSymbol (gene_symbols)
  *gene_id:FK_Gene, *symbol:VARCHAR(64)

ProteinSymbol (protein_symbols)
  *protein_id:FK_Protein, *symbol:VARCHAR(64)

GeneName (gene_names)
  *gene_id:FK_Gene, *name:TEXT

ProteinName (protein_names)
  *protein_id:FK_Protein, *name:TEXT

GeneKeyword (gene_keywords)
  *gene_id:FK_Gene, *keyword:TEXT

ProteinKeyword (protein_keyword)
  *protein_id:FK_Protein, *keyword:TEXT

*(Compound) Primary Key

Requirements
============

- Python 3.2+
- SQLAlchemy 0.7+ (suggested driver: psycopg2)
- Some SQL Database (suggested: PostgreSQL 8.4+)

Setup
=====

TODO Install this script::

    sudo python setup.py install

On a command line, create the database::

    psql -c "DROP DATABASE IF EXISTS gnamed"
    psql -c "CREATE DATABASE gnamed ENCODING='UTF-8'"

Then, download the NCBI Taxonomy file::

    gnamed fetch taxa -d /tmp
    tar zxvf /tmp/taxdump.tar.gz

Boostrap the DB with the taxa file::

    gnamed init /tmp/names.dmp

Usage
=====

Fetch and load any repository as required; e.g.::

    gnamed fetch entrez -d /tmp
    gunzip /tmp/gene_info.gz
    gnamed load entrez /tmp/gene_info

Sometimes, repositories are downloaded as text files; e.g.::

    gnamed fetch hgnc
    gnamed load hgnc hgnc.csv

To see a list of available repositories, use::

    gnamed --list

**Important:** The order in which repositories are loaded *does* matter,
particularly for setting Gene and Protein metadata (chromosome, location,
length, mass). The last repository loaded will always overwrite this metadata.
So it is advisable to first load the generic repositories (Entrez, UniProt)
and only then load the specific ones (HGNC, MGD, RGD, etc.) to set the "true"
metadata.

Fast Loading
============

Given that loading **Entrez Gene** and **UniProt** can take a very long time
(up to a few days) if they are loaded using the default mechanism, a fast DB
dump mechanism (using "``COPY FROM`` stream") is available for those DBs,
circumventing the ORM and its dreadful ``INSERT`` statements. These dumps are
implemented directly with the underlying DB drivers. Thus, only the following
DBs are currently supported with fast loading:

  - PostgreSQL (suffix -pg; driver: **psycopg2**)

To use fast loading, the first repository to load into a just initialized
database (i.e., only containing the NCBI Taxonomy) must be Entrez. Then the
two UniProt files may be fast-loaded and finally all other repositories may be
added (regularly) in any order. To activate the fast loader instead of the
regular Parser/ORM mechanism, append the suffix to the repository key, e.g.,
to fast load Entrez into a Postgres DB use: ``gnamed load entrezpg gene_info``.

Note that if you decide to use SQLight as your DB, the way the ORM dumps data
into it is nearly as quick as using ``COPY FROM`` stream. Therefore, for this
particular DB, fast loading is probably not an issue.

License
=======

GNU `Affero GPL <http://www.gnu.org/licenses/agpl.html>`_ version 3 (aGPLv3)

Copyright: Florian Leitner, 2012. All rights reserved.

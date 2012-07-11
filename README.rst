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

  [Name,Symbol] <- [Protein] <> [Database] <> [Gene] -> [Name,Symbol]
                         |                      |
                         ---------v     v--------
                                 [Species]

Species (species)
  *id:INT, acronym:VARCHAR(64), common_name:TEXT, scientific_name:TEXT

Database (databases)
  *namespace:VARCHAR(32), *accession:VARCHAR(64), version:VARCHAR(16),
  symbol:VARCHAR(64), name:TEXT

Protein (proteins)
  *protein_id:BIGINT, species_id:FK_Species, mass:INT/NULL, length:INT/NULL

Gene (genes)
  *gene_id:BIGINT, species_id:FK_Species, chromosome:VARCHAR(32),
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

License
=======

GNU Affero GPL version 3 (AGPLv3)

(C) Florian Leitner 2012. All rights reserved.

======
gnamed
======
---------------------------------------------------------------------
a command-line tool to bootstrap a database of gene and protein names
---------------------------------------------------------------------

``gnamed`` is a tool to download gene/protein name records, bootstrap a
database to store them, and load the gene/protein names into that datastore,
unifying the names across multiple repositories into single, species-specific
gene and protein records with their references to PubMed IDs. The datastore
differentiates between names and symbols, and contains keywords relevant for
each protein and gene. For genes, their chromosome and location (band) is
stored, while for proteins their weight and length is maintained. The main
("official") name and symbol for each originating repository is retained and
all genes/proteins are linked to their species ID. The references to PubMed
abstracts are collected from the Entrez and UniProt records. For UniProt
records, in addition, all known (i.e. incl. earlier, outdated) accessions are
stored in ``protein_strings`` with the category key (column ``cat``) set to
``"accession"``. After loading, all names and keywords from all repositories,
but mapped to one of the imported repository can be extracted with
``gnamed display``, and mappings between the identifiers ("accessions") of
repositories can be extracted with ``gnamed map``.

Supported Repositories
======================

- **Entrez Gene** (key: ``entrez``)
- **UniProt** (key: ``uniprot``) [to fetch only SwissProt, specify ``swissprot``]
- FlyBase (key: ``flybase``)
- HGNC (key: ``hgnc``)
- MGI/MGD (key: ``mgi``)
- RGD (key: ``rgd``)
- SGD (key: ``sgd``)
- TAIR (key: ``tair``)

Requirements
============

- Python 3 (tested on 3.3+)
- SQL Alchemy 0.7+ (tested: with psycopg2)
- A database (strongly suggested: PostgreSQL 9.1+)

Setup
=====

Requires a database (suggested: PostgreSQL 9.1 or newer).

Install all dependencies/requirements::

    pip install argparse # only for python3 < 3.2
    pip install SQLAlchemy
    pip install psycopg2 # optional, can use any other driver

Install this tool::

    python setup.py install

Create the database::

    psql -c "DROP DATABASE IF EXISTS gnamed_tmp"
    psql -c "CREATE DATABASE gnamed_tmp ENCODING='UTF-8'"
    # or
    dropdb gnamed_tmp
    createdb gnamed_tmp

Then, download the NCBI Taxonomy archive::

    gnamed fetch taxa -d /tmp
    tar zxvf /tmp/taxdump.tar.gz

Boostrap the DB with the NCBI Taxonomy files::

    gnamed init /tmp/nodes.dmp /tmp/names.dmp /tmp/merged.dmp

Usage
=====

Fetch and load any repository as required; e.g.::

    gnamed fetch entrez -d /tmp
    gunzip /tmp/gene_info.gz /tmp/gene2pubmed.gz
    gnamed load entrez /tmp/gene2pubmed /tmp/gene_info

Sometimes, repositories are downloaded as text files; e.g.::

    gnamed fetch hgnc
    gnamed load hgnc hgnc.csv

To see a list of available repositories, use::

    gnamed --list

**Important:** The order in which repositories are loaded *does* matter,
particularly for setting gene and protein metadata (chromosome, location,
length, mass). The last repository loaded will always overwrite this metadata.
So it is advisable to first load the generic repositories (Entrez, UniProt)
and only then load the specific ones (HGNC, MGD, RGD, etc.) to set the "true"
metadata. (I.e., use the order described in the section "Supported
Repositories").

Taxonomy
========

The NCBI Taxonomy is used as the main **species** reference. As some databases
are not always up-to-date, in addition to the default nodes (and their names),
the merged nodes are added, too. This allows mapping of many out-dated TaxIDs
to the relevant (current) species. All (outdated) NCBI TaxIDs that have
been merged into new nodes are added to the **species** table, using the merge
target as their parent_id and with the constant value "``merged``" in the
*rank* attribute, that normally qualifies the type of node. However, there are
records that have no known mapping to the NCBI Taxonomy (and despite being
qualified as NCBI TaxIDs) in some databases. These references to "unknown"
species are all re-mapped to the NCBI node for unknown species (NCBI TaxID
``32644``). For example, in TrEMBL (UniProt), this is the case for about 60
species IDs and their associated proteins.

The **species_names** table contains all names for a given node, using the
attribute *cat* to qualify the type of name (e.g., "``common name``").

Fast Loading
============

Given that loading **Entrez Gene** and **UniProt** can take a very long time
(days or weeks) if they are loaded using the default mechanism, a fast DB
dump mechanism (using "``COPY FROM`` stream") is available for those DBs,
circumventing the ORM and its dreadful ``INSERT`` statements. These dumps are
implemented directly with the underlying DB drivers. Therefore, only the
following DBs are currently supported with fast loading:

- PostgreSQL (suffix -pg; driver: **psycopg2**)

To use fast loading, the first repository to load into a just initialized
database (i.e., only containing the NCBI Taxonomy) must be Entrez. Then the
two UniProt files (or only SwissProt, if you do not want to use TrEMBL) may
be fast-loaded and finally all other repositories should be added in any
preferred order. To activate the fast loader instead of the regular
Parser/ORM mechanism, append the suffix ``pg`` to the repository key,
e.g., to fast load Entrez into a Postgres DB use:
``gnamed load entrezpg gene2pubmed gene_info``.

Note that if you decide to use SQLight as your DB, the way the ORM dumps data
into it is nearly as quick as using ``COPY FROM`` stream. Therefore, for this
particular DB, fast loading is probably not an issue.

Working with UniProt Files
==========================

Particularly loading the TrEMBL data can be daunting, because the corresponding
UniProt flatfile dump is huge (several GB *compressed*). To reduce the size of
the UniProt data, all unnecessary lines can be removed from the dump files::

    zcat uniprot_trembl.dat.gz | grep "^\(ID\|AC\|DE\|GN\|OX\|RX\|DR\|KW\|SQ\|//\)" > uniprot_trembl.min.dat

It is possible to load the UniProt files separately or only load
SwissProt; any file listed as argument will be parsed and loaded::

    gnamed load uniprotpg uniprot_sprot.dat uniprot_trembl.min.dat.gz

Entity Relationship Model
=========================

::

    [SpeciesName] → [Species*]
                         ↑
    [EntityString] → [Entity] ← [EntityRef] | ← [Entity2PubMed]
                       ↑  ↑
                     <mapping>

Species (species)
  **id**:INT, parent_id:FK(Species), *rank*:VARCHAR(32),
  *unique_name*:TEXT, genbank_name:TEXT

SpeciesName (species_names)
  **id**:FK(Species), **cat**:VARCHAR(32), **name**:TEXT

Gene (genes)
  **id**:BIGINT, *species_id*:FK_Species,
  chromosome:VARCHAR(32), location:VARCHAR(64)

Protein (proteins)
  **id**:BIGINT, *species_id*:FK_Species,
  mass:INT, length:INT

mapping (genes2proteins)
  **gene_id**:FK(Gene), **protein_id**:FK(Protein)

EntityRef (entity_refs)
  **namespace**:VARCHAR(8), **accession**:VARCHAR(64),
  symbol:VARCHAR(64), name:TEXT, id:FK(Entity)

Entity2PubMed (entity2pubmed)
  **id**:FK(Entity), **pmid**:INT

EntityString (entity_strings)
  **id**:FK(Entity), **cat**:VARCHAR(32), **value**:TEXT

- **bold** (Composite) Primary Key
- *italic* NOT NULL
- ``Entity`` can be either "Gene" or "Protein"
- ``entity`` can be either "gene" or "protein"


"""
.. py:module:: orm
   :synopsis: .

.. moduleauthor:: Florian Leitner <florian.leitner@gmail.com>
.. License: GNU Affero GPL v3 (http://www.gnu.org/licenses/agpl.html)
"""
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import engine
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.schema import \
    Column, Sequence, ForeignKey, ForeignKeyConstraint, Table
from sqlalchemy.types import Integer, String, Text, BigInteger

_Base = declarative_base()
_db = None
_session = lambda args: None

def initdb(*args, **kwds):
    """
    Create a new DBAPI connection pool.

    The most common and only really required argument is the connection URL

    see sqlalchemy.engine.create_engine

    http://docs.sqlalchemy.org/en/rel_0_7/core/engines.html#sqlalchemy.create_engine
    """
    global _db
    global _session
    _db = engine.create_engine(*args, **kwds)
    _Base.metadata.create_all(_db)
    _session = sessionmaker(bind=_db)
    return None

def Session(*args, **kwds) -> sqlalchemy.orm.session.Session:
    """
    Create a new DBAPI session object.

    see sqlalchemy.orm.session.Session

    http://docs.sqlalchemy.org/en/rel_0_7/orm/session.html#sqlalchemy.orm.session.Session
    """
    return _session(*args, **kwds)

class Species(_Base):

    __tablename__ = 'species'

    id = Column(Integer, primary_key=True)
    acronym = Column(String(64))
    common_name = Column(Text)
    scientific_name = Column(Text)

    genes = relationship('Gene', cascade='all', backref='species')
    proteins = relationship('Protein', cascade='all', backref='species')

    def __init__(self, id:int, common_name:str=None, scientific_name:str=None,
                 acronym:str=None):
        self.id = id
        self.common_name = common_name
        self.scientific_name = scientific_name
        self.acronym = acronym

    def __repr__(self) -> str:
        return "<Species {}>".format(self.id)

    def __str__(self) -> str:
        if self.scientific_name:
            return self.scientific_name
        elif self.common_name:
            return self.common_name
        else:
            return "species:{}".format(self.id)

class Gene(_Base):

    __tablename__ = 'genes'

    id = Column(BigInteger, Sequence('gene_id_seq', optional=True),
                primary_key=True)
    species_id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ), nullable=False)
    location = Column(String(64))
    chromosome = Column(String(32))

    symbols = relationship('GeneSymbol', cascade='all', backref='gene')
    names = relationship('GeneName', cascade='all', backref='gene')

    def __init__(self, species_id:int, location:str=None, chromosome:str=None):
        self.species_id = species_id
        self.location = location
        self.chromosome = chromosome

    def __repr__(self) -> str:
        return "<Gene {} ({})>".format(self.id, self.species_id)

    def __str__(self) -> str:
        return "gene:{}".format(self.id)

class Protein(_Base):

    __tablename__ = 'proteins'

    id = Column(BigInteger, Sequence('protein_id_seq', optional=True),
                primary_key=True)
    species_id = Column(Integer, ForeignKey(
        'species.id', onupdate='CASCADE', ondelete='CASCADE'
    ), nullable=False)
    length = Column(Integer)
    mass = Column(Integer)

    symbols = relationship('ProteinSymbol', cascade='all', backref='protein')
    names = relationship('ProteinName', cascade='all', backref='protein')

    def __init__(self, species_id:int, mass:int=None, length:int=None):
        self.species = species_id
        self.mass = mass
        self.length = length

    def __repr__(self) -> str:
        return "<Protein {} ({})>".format(self.id, self.species)

    def __str__(self) -> str:
        return "protein:{}".format(self.id)

gene_map = Table(
    'db_accessions2gene_ids', _Base.metadata,
    Column('namespace', String(32), primary_key=True),
    Column('accession', String(64), primary_key=True),
    Column('gene_id', BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True),
    ForeignKeyConstraint(
        ['namespace', 'accession'],
        ['databases.namespace', 'databases.accession'],
        onupdate='CASCADE', ondelete='CASCADE'
    )
)

protein_map = Table(
    'db_accessions2protein_ids', _Base.metadata,
    Column('namespace', String(32), primary_key=True),
    Column('accession', String(64), primary_key=True),
    Column('protein_id', BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True),
    ForeignKeyConstraint(
        ['namespace', 'accession'],
        ['databases.namespace', 'databases.accession'],
        onupdate='CASCADE', ondelete='CASCADE'
    )
)

class Database(_Base):

    __tablename__ = 'databases'

    namespace = Column(String(32), primary_key=True)
    accession = Column(String(64), primary_key=True)
    version = Column(String(16))
    symbol = Column(String(64))
    name = Column(Text)

    genes = relationship('Gene', secondary=gene_map, backref='records')
    proteins = relationship('Protein', secondary=protein_map,
                            backref='records')

    def __init__(self, namespace:str, accession:str, version:str=None,
                 symbol:str=None, name:str=None):
        self.namespace = namespace
        self.accession = accession
        self.version = version
        self.symbol = symbol
        self.name = name

    def __repr__(self) -> str:
        return "<Database {}:{}{}>".format(
            self.namespace, self.accession,
            ":{}".format(self.version) if self.version else ""
        )

    def __str__(self) -> str:
        return "{}:{}{}".format(
            self.namespace, self.accession,
            ":{}".format(self.version) if self.version else ""
        )

class GeneName(_Base):

    __tablename__ = 'gene_names'

    gene_id = Column(BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    name = Column(Text, primary_key=True)

    def __init__(self, gene_id:int, name:str):
        self.gene_id = gene_id
        self.name = name

    def __repr__(self) -> str:
        return "<GeneName {} \"{}\">".format(self.gene_id, self.name)

    def __str__(self) -> str:
        return self.name

class GeneSymbol(_Base):

    __tablename__ = 'gene_symbols'

    gene_id = Column(BigInteger, ForeignKey(
        'genes.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    symbol = Column(String(64), primary_key=True)

    def __init__(self, gene_id:int, symbol:str):
        self.gene_id = gene_id
        self.symbol = symbol

    def __repr__(self) -> str:
        return "<GeneSymbol {} {}>".format(self.gene_id, self.symbol)

    def __str__(self) -> str:
        return self.symbol

class ProteinName(_Base):

    __tablename__ = 'protein_names'

    protein_id = Column(BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    name = Column(Text, primary_key=True)

    def __init__(self, protein_id:int, name:str):
        self.protein_id = protein_id
        self.name = name

    def __repr__(self) -> str:
        return "<ProteinName {} \"{}\">".format(self.protein_id, self.name)

    def __str__(self) -> str:
        return self.name

class ProteinSymbol(_Base):

    __tablename__ = 'protein_symbols'

    protein_id = Column(BigInteger, ForeignKey(
        'proteins.id', onupdate='CASCADE', ondelete='CASCADE'
    ), primary_key=True)
    symbol = Column(String(64), primary_key=True)

    def __init__(self, protein_id:int, symbol:str):
        self.protein_id = protein_id
        self.symbol = symbol

    def __repr__(self) -> str:
        return "<ProteinSymbol {} {}>".format(self.protein_id, self.symbol)

    def __str__(self) -> str:
        return self.symbol

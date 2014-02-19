#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='gnamed',
    version='1',
    license='GNU GPL v3',
    author='Florian Leitner',
    author_email='florian.leitner@gmail.com',
    url='https://github.com/fnl/gnamed',
    description='loading and maintaining a gene name database',
    long_description=open('README.rst').read(),
    package_dir={'': 'src'},
    install_requires=[
        'sqlalchemy >= 0.8',
        'pyscopg2 >= 2.3',
        'progress_bar >= 5',
    ],
    packages=[
        'gnamed',
        'gnamed.parsers',
    ],
    scripts=[
        'scripts/gnamed',
    ],
    data_files=[
        ('man/man1', ['gnamed.1']),
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Software Development :: Libraries',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic',
    ],
)

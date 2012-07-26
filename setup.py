#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='gnamed',
    version='1-beta',
    description='A program to bootstrap a gene/protein name repository.',
    license='GNU Affero GPL, latest version',
    author='Florian Leitner',
    author_email='florian.leitner@gmail.com',
    url='http://github.com/fnl/gnamed',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Programming Language :: Python :: 3',
        'Programming Language :: SQL',
        'Intended Audience :: Science/Research',
        'License :: Free for non-commercial use',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX',
        'Topic :: Database',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Scientific/Engineering :: Information Analysis',
    ],
    requires=[ 'SQLAlchemy (>=0.7.8)', 'argparse' ],
    packages=[ 'libgnamed', 'libgnamed.parsers', ],
    scripts=[ 'gnamed' ]
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup
from codecs import open
from os import path
import re

dir_prefix = path.abspath(path.dirname(__file__))

package_name    = "argparse-extd"
module_keywords = {
    'name':         package_name,
    'packages':     [ package_name.replace('-', '_') ],
    'keywords' :    'argparse extenstion',
    'description' : 'Extended argparse.ArgumentParser and Extended argparse.Namespace',
    'license_files': ['LICENSE'],
    'classifiers' : ['Development Status :: 4 - Beta',
                     'License :: OSI Approved :: BSD License',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 3',
                     'Topic :: Software Development :: Libraries :: Python Modules',
                     'Topic :: System :: Software Distribution',
                     'Topic :: Utilities',
                     ],
}

module_keywords['install_requires'] = [ name.rstrip() for name in open('requirements.txt').readlines() ]

def read_module_keywords(fpath:str):
    kwds = ('__copyright__', '__version__', '__license__', 
            '__author__', '__author_email__', '__url__')
    vals = {}
    with open(fpath) as f:
        for line in f:
            for k in kwds:
                if k in line:
                    break
            else:
                continue
            exec(line.rstrip(), globals(), vals)

    ret = { k[2:-2]: vals.get(k) for k in kwds }
    for k in kwds:
        print(k, k[2:-2])
        assert ret[k[2:-2]]
    return ret

module_keywords.update(read_module_keywords(fpath=path.join(dir_prefix, package_name.replace('-', '_'), '__init__.py')))

with open(path.join(dir_prefix, 'README.rst'), encoding='utf-8') as f:
    module_keywords['long_description'] = f.read()

setup(**module_keywords)


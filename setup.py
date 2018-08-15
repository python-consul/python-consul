import glob
import sys
import re
import os

from setuptools.command.test import test as TestCommand
from setuptools.command.install import install
from setuptools import setup

# =============================================================================

requirements = [
    x.strip() for x
    in open('requirements.txt').readlines() if not x.startswith('#')]


description = "Python client for Consul (http://www.consul.io/)"


py_modules = [os.path.splitext(x)[0] for x in glob.glob('consul/*.py')]

# =============================================================================

import pysetup

pysetup.setup_help( __file__, 'pyconsul', description, 'Hunter Gassman','hunter@catalan-analytics.com', license='MIT', long_description=open('README.md').read() + '\n\n' +
        open('CHANGELOG.rst').read()  )

"""
setup(
    name='pyconsul',
    url='https://github.com/cablehead/python-consul',
    license='MIT',
    description=description,
    long_description=open('README.rst').read() + '\n\n' +
        open('CHANGELOG.rst').read(),
    py_modules=py_modules,
)
"""


#!/usr/bin/env python

import os
from setuptools import setup, find_packages
here = os.path.abspath(os.path.dirname(__file__))

install_requires = [
    'simplejson',
    'pyaml',
    'requests'
    ]

test_requires = [
    'testtools',
    'nose',
    'mock',
    ]

setup(name='qubell-api-python-client',
      version='1.30.29.0',  # versionising: <major>.<minor>.<platform major>.<platform minor>
      description='Qubell platform client library',
      long_description=open('README').read(),
      author='Vasyl Khomenko',
      author_email='vkhomenko@qubell.com',
      license=open('LICENSE').read(),
      url='https://github.com/qubell/contrib-python-qubell-client',
      packages=find_packages(exclude=['test_qubell_client', 'stories']),
      package_data={'': ['LICENSE', 'README']},
      include_package_data=True,
      install_requires=install_requires,
      tests_require=test_requires,
      test_suite="nosetests",
     )

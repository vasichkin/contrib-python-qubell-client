#!/usr/bin/env python

import os
from setuptools import setup, find_packages
here = os.path.abspath(os.path.dirname(__file__))
requires = ['simplejson',
            'pyaml',
            'requests',
            'click',
            'colorama']

test_requires = [
    'testtools',
    'nose',
    'mock',
    ]

setup(name='qubell-api-python-client',
      version='1.61.47.25',  # versionising: <major>.<minor>.<platform major>.<platform minor>
      description='Qubell platform client library',
      long_description=open(os.path.join(here,'README')).read(),
      author='Vasyl Khomenko',
      author_email='vkhomenko@qubell.com',
      license=open('LICENSE').read(),
      url='https://github.com/qubell/contrib-python-qubell-client',
      packages=find_packages(exclude=['test_qubell_client', 'stories', 'integration_tests', 'integration_tests.testing']),
      package_data={'': ['LICENSE', 'README', 'requirements.txt', 'qubell/monitor/monitor_manifests/*']},
      include_package_data=True,
      install_requires=requires,
      tests_require=test_requires,
      test_suite="nosetests",
      entry_points='''
        [console_scripts]
        nomi=qubell.cli.__main__:entity
        qubell_monitor = qubell.monitor.monitor:main
    '''
     )

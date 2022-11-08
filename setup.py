#!/usr/bin/env python

import os

from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(HERE, 'README.md')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.md')).read()

tests_require = [
    'factory-boy',
    'flake8',
    'coverage',
]

setup(
    name='django-mapbox-baselayer',
    version=open(os.path.join(HERE, 'mapbox_baselayer', 'VERSION.md')).read().strip(),
    include_package_data=True,
    author="Makina Corpus",
    author_email="geobi@makina-corpus.com",
    description='Django model to store and serve mapbox base layer config',
    long_description=README + '\n\n' + CHANGES,
    description_content_type="text/markdown",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url='https://github.com/makinacorpus/django-mapbox-baselayer.git',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
    ],
    install_requires=[
        'django>=2.2',
    ],
    tests_require=tests_require,
    extras_require={
        'dev': tests_require + [
            'django-debug-toolbar',
        ]
    }
)

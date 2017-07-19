# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='hpcbench',
    version='0.1.0',
    description='Specify and run your benchmarks',
    long_description=readme,
    author='Tristan Carel',
    author_email='tristan.carel@gmail.com',
    url='https://github.com/tristan0x/hpcbench',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)


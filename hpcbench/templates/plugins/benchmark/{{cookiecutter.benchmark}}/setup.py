# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
setup(
    name='hpcbench-{{ cookiecutter.benchmark }}',
    version='0.1',
    description='HPCBench plugin for {{ cookiecutter.benchmark }} benchmark',
    author='{{ cookiecutter.full_name }}',
    author_email='{{ cookiecutter.email }}',
    packages=find_packages(exclude=('tests',)),
    install_requires=[
        'hpcbench>={{ cookiecutter.hpcbench_version }}',
    ],
    entry_points="""
        [hpcbench.benchmarks]
        {{ cookiecutter.benchmark }} = hpcbench_{{ cookiecutter.benchmark }}.benchmark
    """
)

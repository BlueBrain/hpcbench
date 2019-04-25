# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='hpcbench',
    description='Specify and run your benchmarks',
    long_description=readme,
    long_description_content_type='text/x-rst',
    author='Tristan Carel',
    author_email='tristan.carel@epfl.ch',
    url='https://github.com/BlueBrain/hpcbench',
    use_scm_version=True,
    packages=find_packages(exclude=('tests', 'docs')),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Benchmark',
        'Topic :: Utilities',
    ],
    setup_requires=[
        'setuptools_scm==1.15.6',
    ],
    install_requires=[
        'cached-property>=1.3.1',
        'clustershell>=1.8',
        'cookiecutter==1.6.0',
        'docopt==0.6.2',
        'elasticsearch>=6.0.0',
        'jinja2==2.10.1',
        'mock==2.0.0',
        'numpy>=1.13.3',
        'PyYAML>=3.12',
        'python-magic==0.4.15',
        'six>=1.11',
    ],
    include_package_data=True,
    package_data={
        'hpcbench': [
            'benchmark/basic.bash',
            'templates/plugins/benchmark/cookiecutter.json',
            'templates/plugins/benchmark/hooks/pre_gen_project.py',
            'templates/plugins/benchmark/{{cookiecutter.benchmark}}/hpcbench_{{cookiecutter.benchmark}}/benchmark.py',
            'templates/plugins/benchmark/{{cookiecutter.benchmark}}/setup.py',
            'templates/*.jinja',
        ]
    },
    entry_points="""
        [console_scripts]
        ben-csv = hpcbench.cli.bencsv:main
        ben-doc = hpcbench.cli.bendoc:main
        ben-elastic = hpcbench.cli.benelastic:main
        ben-merge = hpcbench.cli.benmerge:main
        ben-nett = hpcbench.cli.bennett:main
        ben-wait = hpcbench.cli.benwait:main
        ben-sh = hpcbench.cli.bensh:main
        ben-tpl = hpcbench.cli.bentpl:main
        ben-umb = hpcbench.cli.benumb:main

        [hpcbench.benchmarks]
        babelstream = hpcbench.benchmark.babelstream
        basic = hpcbench.benchmark.basic
        custream = hpcbench.benchmark.custream
        hpl = hpcbench.benchmark.hpl
        imb = hpcbench.benchmark.imb
        ior = hpcbench.benchmark.ior
        ionvme = hpcbench.benchmark.ionvme
        iperf = hpcbench.benchmark.iperf
        mdtest = hpcbench.benchmark.mdtest
        minigemm = hpcbench.benchmark.minigemm
        nvidia-bandwidthtest = hpcbench.benchmark.nvidia
        osu = hpcbench.benchmark.osu
        shoc = hpcbench.benchmark.shoc
        standard = hpcbench.benchmark.standard
        stream = hpcbench.benchmark.stream
        sysbench = hpcbench.benchmark.sysbench
    """
)

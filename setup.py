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
    author='Tristan Carel',
    author_email='tristan.carel@gmail.com',
    url='https://github.com/tristan0x/hpcbench',
    license=license,
    use_scm_version=True,
    packages=find_packages(exclude=('tests', 'docs')),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
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
        'cached-property==1.3.0',
        'docopt==0.6.2',
        'elasticsearch==5.4.0',
        'jinja2==2.9.6',
        'PyYAML>=3.12',
        'six==1.10',
    ],
    extras_require=dict(
      PLOTTING=['matplotlib==2.0.2'],
    ),
    entry_points="""
        [console_scripts]
        ben-doc = hpcbench.cli.bendoc:main
        ben-elastic = hpcbench.cli.benelastic:main
        ben-nett = hpcbench.cli.bennett:main
        ben-plot = hpcbench.cli.benplot:main [PLOTTING]
        ben-sh = hpcbench.cli.bensh:main
        ben-umb = hpcbench.cli.benumb:main
        [hpcbench.benchmarks]
        sysbench = hpcbench.benchmark.sysbench
        stream = hpcbench.benchmark.stream
    """
)

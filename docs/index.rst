.. sample documentation master file, created by
   sphinx-quickstart on Mon Apr 16 21:22:43 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

HPCBench Documentation
======================

.. module:: hpcbench

HPCBench is a Python package that allows you to specify and execute benchmarks. It provides:

* an API to describe how to execute benchmarks utilities and gather metrics.
* A way to describe tests campaigns in a YAML format.
* command line executable to execute your campaigns, and use generated metrics for
  various usage:

   * Plotting with matplotlib
   * PDF report generation
   * Elasticsearch / Kibana integration

HPCBench does not support benchmark softwares installation.

This Python package is still in pre-alpha stage, and not suitable for production.

Installation
============
.. highlight:: bash

**HPCBench** is in the `Python Package Index <http://pypi.python.org/pypi/hpcbench/>`_.

Installation with pip
---------------------

We recommend using `pip <http://pypi.python.org/pypi/pip>`_ to install hpcbench on all platforms::

  $ python -m pip install hpcbench

To upgrade using pip::

  $ python -m pip install --upgrade hpcbench

Dependencies
------------

HPCBench support 2.7, and 3.4+.


Overview
========

CLI
---

**HPCBench** provides a set of command line utilities:

* ben-sh: Execute a tests campaign
* ben-umb: Extract metrics of an existing campaign
* ben-plop: Draw figures of an existing campaign
* ben-elk: Push campaign data to Elasticsearch

**ben-sh** expects a :doc:`YAML file <campaign>` describing the campaign to execute.

API
---

HPCBench API purpose is to provide an unified layer:

* to execute, and parse results of existing benchmarks utilities (Linpack, IOR, ...)
* to use extracted metrics to build figures

Development Guide
-----------------

Prerequisites
~~~~~~~~~~~~~

`Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ is required to execute unit-tests. The easiest way to proceed is
to use Docker containers.

Quick'n dirty Docker installation::

   $ curl -fsSL get.docker.com -o get-docker.sh
   $ sh get-docker.sh
   $ curl -L https://github.com/docker/compose/releases/download/1.15.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
   $ chmod +x /usr/local/bin/docker-compose

Post-installation instructions to use Docker without root privileges (logout/login) required::

   $ sudo groupadd docker
   $ sudo usermod -aG docker $USER


To start an Elasticsearch container, you can use the
``misc/docker-elk.yaml`` file::

   $ docker-compose -f misc/docker-elk.yaml up -d elasticsearch

Let's try to ping Elasticsearch::

   $ curl localhost:9200
   {
     "name" : "jQ-BcoF",
     "cluster_name" : "elasticsearch",
     "cluster_uuid" : "yGP7_Q2gSU2HmHpnQB-jzg",
     "version" : {
       "number" : "5.5.1",
       "build_hash" : "19c13d0",
       "build_date" : "2017-07-18T20:44:24.823Z",
       "build_snapshot" : false,
       "lucene_version" : "6.6.0"
     },
     "tagline" : "You Know, for Search"
   }

Build instructions
~~~~~~~~~~~~~~~~~~
.. highlight:: bash

Grab the source code::

  $ git clone https://github.com/tristan0x/hpcbench.git
  $ cd hpcbench

It is then suggested to use a dedicated virtual environment. For that you can use
either `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ package or
`pyenv <https://github.com/pyenv/pyenv>`_, which is even better.

With ``pyenv``::

  $ pyenv virtualenv hpcbench
  $ pyenv local hpcbench

With ``virtualenv``::

   $ virtualenv .env
   $ . .env/bin/activate

Then::

  $ pip install tox
  $ tox -e py27

``tox`` is configured to test HPCBench against different Python versions. Option
``-e py27`` tells tox to only test against Python 2.7.

How to start Elasticsearch cluster?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Elasticsearch is required to pass unit-tests.
You can use ``misc/docker-elk.yaml`` docker-compose file::

   $ docker-compose -f misc/docker-elk.yaml up -d


It will start an Elasticsearch container listening on port 9200 and a Kibana
instance listening on port 5612.

Unit-tests assume that Elasticsearch is running on localhost. 
You can define ``UT_ELASTICSEARCH_HOST`` environment variable to specify
another location::

   $ ELASTICSEARCH_HOST=server01:9200 tox

How to integrate a new benchmark utility?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. First make sure you can properly build the project and tests pass successfully.
   It may be tempting to skip this part, but please don't.
2. Create a dedicated Git branch.
3. Create a dedicated Python module in ``hpcbench/benchmark`` directory.
4. Implement ``hpcbench.api.Benchmark`` and ``hpcbench.MetricsExtractor`` classes
5. Register the new module in ``setup.py`` ``[hpcbench.benchmarks]`` entrypoint
   so that it can be introspectable.
6. Create a dedicate tests class in `tests/benchmark/` directory.
   Purpose of this test is to make sure that:

   * your Benchmark class is properly defined, and usable by HPCBench.
   * your metric extractor is properly working, without having to launch the
     utility itself.
7. To properly test your metrics extractors, some outputs of the benchmark utility
   will be added to the repository. For every category of your benchmark, create a 
   file title ``tests/benchmark/<test_module_name>.<category>.stdout`` with the
   benchmark utility output. These files will be automatically used.
   Do not hesitate to take inspiration from ``tests/benchmark/test_sysbench.py``
   test module.

8. Run the test-suites until it passes::

   $ tox

9. Submit a `pull-request <https://github.com/tristan0x/hpcbench>`_

LICENSE
=======

This software is released under MIT License.

Contents:

.. toctree::
   :maxdepth: 2

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. sample documentation master file, created by
   sphinx-quickstart on Mon Apr 16 21:22:43 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

HPCBench Documentation
======================

.. module:: hpcbench

HPCBench is a Python package that allows you to specify and execute benchmarks. It provides:

* an API to describe how to execute benchmarks utilities and gather metrics.
* A way to describe benchmark campaigns in YAML format.
* command line utilities to execute your campaigns, and post-process generated metrics in
  various ways:

   * Merging metrics from different campaigns
   * Exporting metrics in CSV format
   * Exporting data to Elasticsearch
   * PDF report generation

HPCBench assumes that the various benchmark tools/binaries are managed elsewhere and does
not provide features for building and maintaining benchmark software.

NB: This Python package is still in pre-alpha stage, and not suitable for production.

Installation
============
.. highlight:: bash

**HPCBench** is in the `Python Package Index <http://pypi.python.org/pypi/hpcbench/>`_.

Installation with pip
---------------------

We recommend using `pip <http://pypi.python.org/pypi/pip>`_ to install hpcbench on all platforms::

  $ python -m pip install hpcbench

To upgrade HPCBench with pip::

  $ python -m pip install --upgrade hpcbench

Dependencies
------------

HPCBench supports both python 2.7 and 3.4+.


Overview
========

CLI
---

The main interface through which **HPCbench** is used is a set of command
line utilities:

* ben-sh: Execute a tests campaign on your workstation
* ben-csv: Extract metrics of an existing campaign in csv format
* ben-umb: Extract metrics of an existing campaign
* ben-elastic: Push campaign data to Elasticsearch
* ben-nett: Execute a tests campaign on a cluster
* ben-merge: Merge campaign output directories
* ben-tpl: Generate HPCBench plugin scaffolds,
  see :ref:`usage <ben-tpl-usage>` for more information on plugin generation.

**ben-sh** and **ben-nett** expect a YAML file describing the campaign to execute.
The structure of this YAML file is detailed in the :doc:`campaign file reference <campaign>`.

Campaign YAML description
-------------------------

.. toctree::
   :maxdepth: 2
   :numbered:

   campaign.rst
   standard_benchmark.rst

API
---

The purpose of the HPCBench API is to provide a consistent and unified layer:

* to execute, and parse results of existing benchmarks utilities (Linpack, IOR, ...)
* to use extracted metrics to build figures

Both system benchmarks (e.g. STREAM, linpack), as well as software benchmarks should be
implemented using this API. Most users parametrize benchmarks in the above-mentioned
campaign YAML file. More advanced users will want to implement their own benchmarks based
on the API.

For more information check the :doc:`module reference <modules>`

Getting Started
===============

As of now, only a few benchmarks are supported. This section assumes that
you have at least installed the ``sysbench`` utility on your workstation.

Launch a campaign on your workstation
-------------------------------------

Create your first campaign YAML file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``local-campaign.yaml`` file with the following content::

   benchmarks:
     '*':
       test:
         type: sysbench

Launch the benchmark on your workstation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the following command::

   $ ben-sh local-campaign.yaml


This will create a ``hpcbench-<date>`` in the directory with the benchmark's results.
Although the user is not meant to be manually checking results inside the output directory
at this point take a look at ``hpcbench-<date>/<hostname>/*/test/metrics.json``. You will
find that this file contains the collected metrics data from sysbench. The raw logs and
stdout's can be found further down the directory tree.

**Note**: Do not manually edit files inside the output directory. HPCBench offers a number of
utilities to export and post-process the collected results.

Launch a campaign on a set of nodes
-----------------------------------

The YAML config file is getting a little more complex. For instance create
the following ``remote-campaign.yaml``::

   network:
     nodes:
       - localhost
   benchmarks:
     '*':
       test:
         type: sysbench

You can add computer nodes to the ``nodes`` section.

Launch the benchmark
~~~~~~~~~~~~~~~~~~~~

Use the ``ben-nett`` utility to execute the campaign on every nodes.
It uses SSH to submit jobs so you have to make sure you can access those
nodes without passphrase. For this you could use the ``ssh_config_file`` key in YAML to
specify a custom configuration (see) :doc:`campaign file reference <campaign>`)::

   $ ben-nett remote-campaign.yaml

.. _ben-tpl-usage:

How to create a new benchmark Python module?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to create your own benchmark based on a tool that has not been so far supported
by HPCBench. This is done by generating an external plugin scaffold using ``ben-tpl`` and
implementing the benchmark execution and metrics parsing inside the generated classes.

Here is the basic workflow:

1. First create a default JSON file describing the Python module:
    ``ben-tpl benchmark -g config.json``
2. Update fields in ``config.json``
3. Generate the Python module template in the current directory:
    ``ben-tpl benchmark config.json``
4. Edit the ``benchmark.py`` file
5. When ready you can install the module, with ``pip`` for instance.

Development Guide
=================

Prerequisites
-------------

Docker
~~~~~~

`Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ is required to execute
some of the unit-tests. The easiest way to accomplish this, is to use Docker containers.

Quick'n'dirty Docker installation::

   $ curl -fsSL get.docker.com -o get-docker.sh
   $ sh get-docker.sh
   $ curl -L https://github.com/docker/compose/releases/download/1.15.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
   $ chmod +x /usr/local/bin/docker-compose

Post-installation instructions to use Docker without root privileges (logout/login) required::

   $ sudo groupadd docker
   $ sudo usermod -aG docker $USER

Test your docker installation with::

    $ docker run --rm hello-world


Build instructions
------------------
.. highlight:: bash

Grab the source code::

  $ git clone https://github.com/BlueBrain/hpcbench.git
  $ cd hpcbench

We suggest you use a dedicated virtual environment. For that you can use
either `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ package or
`pyenv <https://github.com/pyenv/pyenv>`_, which is even better.

With ``pyenv``::

  $ pyenv virtualenv hpcbench
  $ pyenv local hpcbench

Alternatively, with ``virtualenv``::

   $ virtualenv .env
   $ . .env/bin/activate

Then::

  $ pip install tox
  $ tox -e py27

``tox`` is configured to test HPCBench against different Python versions. To test against a
specific python version you can supply it the ``-e`` parameter::

  $ tox -e py27 --
  $ tox -e py36 --

The ``--tests`` parameter can be used to run only one specific unit test module or class::

  $ tox  -e py36 -- --tests tests/test_driver.py

Elasticsearch
~~~~~~~~~~~~~

To start an Elasticsearch container, you can use the
``misc/dc`` script wrapper on top of ``docker-compose``::

   $ misc/dc up -d

It will start an Elasticsearch container listening on port 9200 and a Kibana
instance listening on port 5612.

Let's now try to ping Elasticsearch::

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

You can also access Kibana at http://localhost:5601
The ``Dev Tools`` is one of the most handy Elasticsearch client for humans.

Testing it all out
~~~~~~~~~~~~~~~~~~

Unit-tests assume that Elasticsearch is running on localhost.
You can define the ``UT_ELASTICSEARCH_HOST`` environment variable to specify
another location::

   $ ELASTICSEARCH_HOST=server01:9200 tox

How to integrate a new benchmark utility in the HPCBench repository?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. First make sure you can properly build the project and tests pass successfully.
   It may be tempting to skip this part, but please don't.
2. Create a dedicated Git branch.
3. Create a new Python module in ``hpcbench/benchmark`` directory named after the
   utility to integrate.
4. In this new module, implement ``hpcbench.api.Benchmark`` and
   ``hpcbench.MetricsExtractor`` classes.
5. Register the new module in ``setup.py`` ``[hpcbench.benchmarks]`` entrypoint
   so that it can be found by HPCBench.
6. Create a dedicated unit test class in `tests/benchmark/` directory.
   The purpose of this test is to make sure that:
   * your Benchmark class is properly defined, and usable by HPCBench.
   * your metric extractor is properly working, without having to launch the
     utility itself.
7. To properly test your metrics extractors, some outputs of the benchmark utility
   will be added to the repository. For every category of your benchmark, create a
   file title ``tests/benchmark/<test_module_name>.<category>.stdout`` with the
   benchmark utility's output. These files will be automatically used.
   Do not hesitate to take inspiration from the ``tests/benchmark/test_sysbench.py``
   test module.

8. Run the test-suites until it passes::

   $ tox

9. Submit a `pull-request <https://github.com/BlueBrain/hpcbench>`_

LICENSE
=======

This software is released under MIT License.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

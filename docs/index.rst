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

* ben-sh: Execute a tests campaign on your workstation
* ben-umb: Extract metrics of an existing campaign
* ben-plop: Draw figures of an existing campaign
* ben-elastic: Push campaign data to Elasticsearch
* ben-nett: Execute a tests campaign on a cluster

**ben-sh** and **ben-nett** expect a YAML file describing the campaign to execute.
Structure of this YAML file is detailled in the :doc:`campaign file reference <campaign>`.

API
---

HPCBench API purpose is to provide an unified layer:

* to execute, and parse results of existing benchmarks utilities (Linpack, IOR, ...)
* to use extracted metrics to build figures

Getting Started
===============

As of now, only a few benchmark utilities are supported. This section assumes that
you installed ``sysbench`` utility on your workstation.

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


This will create a ``hpc-bench-<date>`` in the directory with the benchmark's results.

Build the plots
~~~~~~~~~~~~~~~

You can use the ``ben-plot`` utility to generate figures from a campaign's data::

   $ ben-plot <path_to_created_directory>

Some PNG will be generated in the given directory.

Launch a campaign on a set of servers
-------------------------------------

The YAML config file is getting a little more complex. For instance create
the following ``remote-campaign.yaml``::

   network:
     nodes:
       - localhost
   benchmarks:
     '*':
       test:
         type: sysbench

You can add servers to the ``nodes`` section.

Launch the benchmark
~~~~~~~~~~~~~~~~~~~~

Use the ``ben-nett`` utility to execute the campaign on every nodes.
It uses SSH to submit jobs so you have to sure you can access those servers without passphrase. You can use the ``ssh_config_file`` key in YAML to specify a custom
configuration (see) :doc:`campaign file reference <campaign>`)::

   $ ben-nett remote-campaign.yaml

Development Guide
=================

Prerequisites
-------------

Elasticsearch
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

Build instructions
------------------
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

How to add a new plots to an existing benchmark?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install `hpcbench` on a server where the benchmark utility is installed.
2. Execute a campaign on this server with ``ben-sh``.
3. Retrieve the campaign data on your workstation.
4. Setup development environment on your workstation.
5. Install the module in `editable` mode with the following command::

   $ pip install -e '.[PLOTTING]'

6. Now you can test your plotting methods with the following command::

   $ .env/bin/ben-plot PATH_TO_CAMPAIGN

   The command uses the current working-copy to render figures of the campaign.
   So every change your make is taken into account immediately.

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

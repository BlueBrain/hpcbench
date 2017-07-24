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

HPCBench support 2.7, and 3.3+.


Overview
========

CLI
---

**HPCBench** provides a set of command line utilities:

* ben-sh: Execute a tests campaign
* ben-umb: Extract metrics of an existing campaign
* ben-plop: Draw figures of an existing campaign

**ben-sh** expects a :doc:`YAML file <campaign>` describing the campaign to execute.

API
---

HPCBench API purpose is to provide an unified layer:

* to execute, and parse results of existing benchmarks utilities (Linpack, IOR, ...)
* to use extracted metrics to build figures

Development Guide
-----------------

How to integrate a new benchmark utility?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a dedicated module in ``hpcbench/benchmark`` directory
2. Implement ``hpcbench.api.Benchmark`` and ``hpcbench.MetricsExtractor`` classes
3. Add dedicated tests in `tests/benchmark` directory. You can reuse tests of
   sysbench benchmark utility. Your test should not expect the wrapped benchmark utility to be installed.
4. Register the new module in ``setup.py`` ``[hpcbench.benchmarks]`` entrypoint.

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


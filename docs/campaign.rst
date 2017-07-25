HPCBench Campaign file reference
================================

HPCBench uses a YAML file
(see `YAML cookbook <http://yaml.org/YAML_for_ruby.html>_`)
to describe a tests campaign.
Topics of this reference page are organized by top-level key
to reflect the structure of the Campaign file itself.

Network configuration reference
-------------------------------

A Campaign is made of a set of nodes to benchmarks. Those nodes
can be tagged create groups, that can be later used to 
filter nodes where benchmarks are executed.

nodes
~~~~~
Specify which nodes are involved in the tests campaign.
Here is an sample describing a cluster of 2 nodes.

.. code-block:: yaml
  :emphasize-lines: 2

  network:
    nodes:
      - srv01
      - srv02
      - gpu-srv01
      - gpu-srv02

tags
~~~~
Specify groups of nodes.

A tag can be defined with either an exaustive list of a regular expression.

For instance, given the set of nodes defined above, we can define the
*cpu* and *gpu* tags as follow:

.. code-block:: yaml
  :emphasize-lines: 7,8,12

  network:
    nodes:
      - srv01
      - srv02
      - gpu-srv01
      - gpu-srv02
    tags:
      cpu:
        nodes:
          - srv1
          - srv2
      gpu:
        match: gpu-.*

Both methods are being used:

* **nodes** expects an exaustive list of nodes.
* **match** expects a valid regular expression

Benchmarks configuration reference
----------------------------------

The **benchmarks** section specifies benchmarks to execute
on every tag.

* key: the tag name. "*" matches all nodes described 
  in the *network.nodes* section.
* value: a dictionary of name -> benchmark description.
  Each key must be tag names, values is another
  dictionary.

.. code-block:: yaml

  benchmarks:
    cpu:
      test_cpu:
        type: sysbench
    '*':
      check_ram
        type: random_ram_rw

Benchmark configuration reference
---------------------------------

Specify a benchmark to execute.

type
~~~~
Benchmark name.

.. code-block:: yaml
  :emphasize-lines: 4

  benchmarks:
    cpu:
      test_cpu:
        type: sysbench

attributes (optional)
~~~~~~~~~~~~~~~~~~~~~
*kwargs** arguments given to the benchmarch Python class constructor to
override default behavior.

.. code-block:: yaml
  :emphasize-lines: 5

  benchmarks:
    gpu:
      test_gpu:
        type: sysbench
        attributes:
          features:
          - gpu

environment (optional)
~~~~~~~~~~~~~~~~~~~~~~
A dictionary to add environment variables.
Any boolean values; true, false, yes not, need to be enclosed in quotes to ensure
they are not converted to True or False by YAML parse.

.. code-block:: yaml
  :emphasize-lines: 5

  benchmarks:
    '*':
      test_cpu:
        type: sysbench
        environment:
          TEST_ALL: 'true'
          LD_LIBRARY_PATH: /usr/local/lib64

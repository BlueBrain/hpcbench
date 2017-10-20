HPCBench Standard Benchmark
===========================

The "standard" benchmark is a general purpose benchmark.
Its configuration is passed thru the ``attributes`` field in the
YAML campaign file.

It is made of 3 top attributes, each of one being a dictionary:

* **metrics**: specifies how to extract information from command output
* **executables**: describe the commands to execute
* **shells** (optional): provide more flexibility to build the commands to execute

Metrics configuration reference
-------------------------------

This section specifies the metrics the benchmark has to extract from
command outputs, as dictionary "name" -> "configuration"

A metric configuration is a dictionary made of the following keys:

match
~~~~~

The regular expression used to extract the value from the program execution
output. The expression must specify one and only one group used to extract
the proper value.

The string to match has trailing whitespace removed.

type
~~~~

The metric type, as specified in the `hpcbench.API.Metric`

multiply_by (optional)
~~~~~~~~~~~~~~~~~~~~~~

If any, the extracted value will be multiplied by the specified value. It is
useful to convert a unit, for instance from flop to Gflop.

category (optional)
~~~~~~~~~~~~~~~~~~~

The benchmark category the metric applies to. Default is ``standard``.

from (optional)
~~~~~~~~~~~~~~~

Specifies the output file to look for. Default is ``stdout``.

when (optional)
~~~~~~~~~~~~~~~

Provides a way to override fields above according to the metas of the executed command.
Conditions may be declared as a list, the first condition evaluated to ``true`` providing
a given property is used.

A condition is a dictionary composed of the following attributes:

* conditions: a dictionary of "meta_name" -> "value" where value is either a value of a list
  of values.
* match, multiply_by, from (optional): provide value that supersedes default one if conditions
  above are met.

For instance:

.. code-block:: yaml

  benchmarks:
    '*':
      my-test:
        type: standard
        attributes:
          metrics:
            simulation_time:
              match: "\\s+total compute time:\\s(\\d*\\.?\\d+) \\[ms\\]"
              type: Second
              multiply_by: 0.001
              when:
              -
                conditions:
                  compiler: [gcc, icc]
                  branch: feat/bump-performance
                match: "\\s+total pool clone time:\\s(\\d*\\.?\\d+) \\[ms\\]"
                multiply_by: 1.0


This example describes how the ``simulation_time`` metric has to be extracted and computed.
In the general case:

* the regular expression used to extract the metric is the
  "... total compute time" expression
* The type of the metrics is ``Metric.Second``
* The extracted value will by multiplied by 0.001

But when the *compiler* metas is either "gcc" or "icc" **and** when the
*branch* meta is "feat/bump_performance":

* the regular expression is different
* the multiplication factor is 1

Executables configuration reference
-----------------------------------

This section specifies the commands the benchmark has to execute. It is made of a list
of dictionaries. Each dictionary describes a set of commands to run. They are
composed of the following keys:

command
~~~~~~~

Describes the command to launch. It must be a list of elements. Elements
support the `Python Format Specification Mini-Language <https://docs.python.org/2/library/string.html#format-specification-mini-language>`_ where the possible attributes are the metas
describe below.

metas
~~~~~

A list of dictionary or the dictionary itself if this is the only one.
Each dictionary describes a set of metas values.

.. code-block:: yaml

  executables:
  -
    command: [echo, {foo}, {bar}]
    metas:
    -
      foo: 1
      bar: [2, 3]
    - foo: [4, 5]
      bar: [6, 7]

Using a list of values allows you to describe a combination of commands. In the example above, it means
launchning 6 commands:

* ``echo 1 2``
* ``echo 1 3``
* ``echo 4 6``
* ``echo 4 7``
* ``echo 5 6``
* ``echo 5 7``


category (optional)
~~~~~~~~~~~~~~~~~~~

A category to ease classification. Default value is "standard".

Shells configuration reference
------------------------------

This sections describes a list of commands that may prefix the commands specified in the ``executables``
section. It is composed of a list of dictionary. Each dictionary is made of the following keys:

commands
~~~~~~~~

A list of shell commands, for instance

.. code-block:: yaml

  shells:
  - commands:
    - . /usr/share/lmod/lmod/init/bash
    - . $SPACK_ROOT/share/spack/setup-env.sh
    - spack install myapp@{branch} %{compiler}
    - spack load myapp@{branch} %{compiler}

Specified commands also support the `Python Format Specification Mini-Language <https://docs.python.org/2/library/string.html#format-specification-mini-language>`_ to use
the metas of execution context. Those metas can be either those define in the ``shells`` or
``executables`` section.

metas
~~~~~

Provides either a list of a dictionary providing additional metas values or
the dictionary itself if this is the sole dictionary. Like in the ``executables`` section,
it describes a combination of metas.

.. code-block:: yaml

  shells:
  - commands:
    - . /usr/share/lmod/lmod/init/bash
    - . $SPACK_ROOT/share/spack/setup-env.sh
    - spack install myapp@{branch} %{compiler}
    - spack load myapp@{branch} %{compiler}
    metas:
      compiler: [gcc, icc]

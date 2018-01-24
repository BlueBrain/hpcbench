HPCBench Campaign file reference
================================

HPCBench uses a YAML file
(see `YAML cookbook <http://yaml.org/YAML_for_ruby.html>`_)
to describe a tests campaign.
Topics of this reference page are organized by top-level key
to reflect the structure of the Campaign file itself.

output_dir
----------

This top-level attribute specifies the output directory
where HPCBench stores the benchmark results.
Default value is "hpcbench-%Y%m%d-%H:%M:%S"
You can also specify some variables enclosed in braces.
Because of environment variable

* node: value of ben-sh "-n" option.

For instance for a daily report with the node name inside
the directory, you can use: "hpcbench-{node}-%Y%m%d"

Network configuration reference
-------------------------------

A Campaign is made of a set of nodes to benchmarks. Those nodes
can be tagged to create groups, later used to
filter nodes where certain benchmarks are executed on.

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


Nodes can also be specified using the
`ClusterShell <http://clustershell.readthedocs.io/en/latest/tools/nodeset.html#usage-basics>`_
`NodeSet` syntax. For instance

.. code-block:: yaml
  :emphasize-lines: 3

  network:
    nodes:
      - srv[0-1,42,060-062]

is equivalent to:

.. code-block:: yaml

  network:
    nodes:
    - srv0
    - srv2
    - srv42
    - srv060
    - srv061
    - srv062

tags
~~~~
Specify groups of nodes.

A tag can be defined with either an exhaustive list or a regular expression.

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

* **nodes** expects an exhaustive list of nodes. The
  `ClusterShell <http://clustershell.readthedocs.io/en/latest/tools/nodeset.html#usage-basics>`_
  `NodeSet` syntax is also supported.

* **match** expects a valid regular expression

ssh_config_file
~~~~~~~~~~~~~~~

Optional path to a custom SSH configuration file (see man ssh_config(5)).
This can be used to provide HPCBench access to cluster nodes without passphrase
by using a dedicated SSH key.

For instance::

   Host *.my-cluster.com
   User hpc
   IdentityFile ~/.ssh/hpcbench_rsa

remote_work_dir
~~~~~~~~~~~~~~~

Working path on remote nodes. Default value is ``.hpcbench``
Relative paths are relative from home directory.

installer_template
~~~~~~~~~~~~~~~~~~

Jinja template to use to generate the shell-script installer
deployed on cluster's nodes. Default value is ``ssh-installer.sh.jinja``

installer_prelude_file
~~~~~~~~~~~~~~~~~~~~~~

Optional path to a text file that will be included at the beginning
of the generated shell-script installer.
This can be useful to prepare the working environment, for instance to make
Python 2.7, or Python 3.3+ available in ``PATH`` environment variable if this
is not the case by default.

max_concurrent_runs
~~~~~~~~~~~~~~~~~~~

Number of concurrent benchmarks executed in parallel in the cluster.
Default is 4.

pip_installer_url
~~~~~~~~~~~~~~~~~

HPCBench version to install on nodes. By default it is the current ``ben-nett``
version managing the cluster. This is an argument given to ``pip`` installer, here are a some examples:

* ``hpcbench==2.0`` to force a version available PyPi
* ``git+http://github.com/tristan0x/hpcbench@master#egg=hpcbench`` to install the bleeding edge version.
* ``git+http://github.com/me/hpcbench@feat/awesome-feature#egg=hpcbench`` to deploy a fork's branch.

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
*kwargs** arguments given to the benchmark Python class constructor to
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

exec_prefix (optional)
~~~~~~~~~~~~~~~~~~~~~~
Command prepended to every commands spawned by the tagged benchmark. Can 
be either a string or a list of string, for instance:

.. code-block:: yaml
  :emphasize-lines: 4

  benchmarks:
    cpu:
      mcdram:
        exec_prefix: numactl -m 1
        type: stream

srun_options
~~~~~~~~~~~~

When the `srun` execution layer is enabled, a list of providing additional
options given to the `srun` command.

attempts (optional)
~~~~~~~~~~~~~~~~~~~
Dictionary to specify the number of times a command must be executed before
retrieving its results. Those settings allow benchmark execution on warm caches.
Number of times can be either specified statically or dynamically.

The static way to specify the number of times a command is executed is through
the ``fixed`` option.

.. code-block:: yaml
  :emphasize-lines: 5-6

  benchmarks:
      '*':
          test01:
              type: stream
              attempts:
                  fixed: 2


The dynamic way allow you to execute the same command over and over again
until a certain metric converges. The convergence condition is either fixed
with the ``epsilon`` parameter or relative with ``percent``.

.. code-block:: yaml
  :emphasize-lines: 6-8

  benchmarks:
      '*':
          test01:
              type: stream
              attempts:
                  metric: bandwidth
                  epsilon: 50
                  maximum: 5

Every commands of the ``stream`` benchmark will be executed:

* as long as the difference of ``bandwidth`` metric between two consecutive
  runs is above 50.
* at most 5 times


.. code-block:: yaml
  :emphasize-lines: 6-8

  benchmarks:
      '*':
          test01:
              type: stream
              attempts:
                  metric: bandwidth
                  percent: 10
                  maximum: 5

Every commands of the ``stream`` benchmark will be executed:

* as long: ``abs(bandwidth(n) - bandwidth(n - 1)) < bandwidth(n) * percent / 100``
* at most 5 times

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

cwd (optional)
~~~~~~~~~~~~~~
Specifies a custom working directory.

metrics (optional)
~~~~~~~~~~~~~~~~~~
Additional metrics to put in the benchmark report.

.. code-block:: yaml
  :emphasize-lines: 5-6

  benchmarks:
    '*':
      test_cpu:
        type: sysbench
        metrics:
          family: kaby_lake
          l1_cache: 32
          l2_cache: 256

Precondition configuration reference
------------------------------------
This section specifies conditions to filter benchmarks execution.

.. code-block:: yaml
  :emphasize-lines: 11-15

  benchmarks:
    '*':
      cpu_numactl_0:
        exec_prefix: [numctl, -m, 0]
        type: stream
      cpu_numactl_1:
        exec_prefix: [numctl, -m, 1]
        type: stream
      disk:
        type: mdtest
  precondition:
    cpu_numactl_0: HPCBENCH_MCDRAM
    cpu_numactl_1:
      - HPCBENCH_MCDRAM
      - HPCBENCH_CACHE

* **cpu_numactl_0** benchmark needs the ``HPCBENCH_MCDRAM`` environment
  to be defined for being executed.
* **cpu_numactl_1** benchmark needs either ``HPCBENCH_MCDRAM`` or
  ``HPCBENCH_CACHE`` environment variables to defined for being executed.
*  **disk** benchmark will be executed in all cases.

Process configuration reference
-------------------------------
This section specifies how ``ben-sh`` execute the benchmark commands.

type (optional)
~~~~~~~~~~~~~~~
A string indicating the execution layer. Possible values are:

* ``local`` (default) to spawn processes where ``ben-sh`` is running.
* ``srun`` to use `srun <https://slurm.schedmd.com/srun.html>`_ to launch
  processes.

config (optional)
~~~~~~~~~~~~~~~~~
This dictionary provides the execution layer configuration.

The ``srun`` layer accepts the following keys:

* ``srun`` (optional) a string indicating the path to srun executable
* ``srun_options`` a list of string providing the options given to every srun commands. It is the proper place to specify the account name for instance.

.. code-block:: yaml

  process:
    type: srun
    config:
      srun_options:
        - --account=project42
        - --partition=über-cluster

Environment variable expansion
------------------------------

Your configuration options can contain environment variables. HPCBench uses the
variable values from the shell environment in which `ben-sh` is run. 
For example, suppose the shell contains EMAIL=root@cscs.ch and you supply this configuration:

.. code-block:: yaml

  process:
    type: srun
    config:
      srun_options:
        - --email=$EMAIL
        - --partition=über-cluster


When you run ben-sh with this configuration, the program looks for the EMAIL
environment variable in the shell and substitutes its value in.

If an environment variable is not set, substitution fails and an exception is raised.

Both $VARIABLE and ${VARIABLE} syntax are supported. Additionally,  it is possible to provide inline default values using typical shell syntax:

${VARIABLE:-default} will evaluate to default if VARIABLE is unset or empty in the environment.
${VARIABLE-default} will evaluate to default only if VARIABLE is unset in the environment.
${#VARIABLE} will evaluate to the length of the environment variable.
Other extended shell-style features, such as ${VARIABLE/foo/bar}, are not supported.

You can use a $$ (double-dollar sign) when your configuration needs a literal dollar sign.
This also prevents HPCBench from interpolating a value, so a $$ allows you to
refer to environment variables that you don’t want processed by HPCBench.

HPCBench Campaign file reference
================================

HPCBench uses a YAML file
(see `YAML cookbook <http://yaml.org/YAML_for_ruby.html>`_)
to describe a benchmark campaign.
Topics of this reference page are organized by top-level key
to reflect the structure of the Campaign file itself.

output_dir
----------

This top-level attribute specifies the output directory
where HPCBench stores the benchmark results.
The default value is "hpcbench-%Y%m%d-%H%M%S"
You can also specify some variables enclosed in braces, specifically:

* node: value of ben-sh "-n" option.

This also includes environment variables (prefixed with $).
For instance for a daily report with the node name inside
the directory, you can use: "hpcbench-{node}-$USER-%Y%m%d"

Network configuration reference
-------------------------------

A Campaign is made of a set of nodes that will be benchmarked. Those nodes
can be tagged to create groups of nodes. The tags are used to constrain
benchmarks to be run on subsets of nodes.

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

A tag can be defined with an explicit node list, a regular expression of node names,
a recursive to other tags, or a SLURM constraint.

For instance, given the set of nodes defined above, we can define the
*cpu* and *gpu* tags as follow:

.. code-block:: yaml
  :emphasize-lines: 7,8,12,14,16

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
      all-cpus:
        constraint: skylake
      all:
        tags: [cpu, gpu]

All methods are being used:

* **nodes** expects an exhaustive list of nodes. The
  `ClusterShell <http://clustershell.readthedocs.io/en/latest/tools/nodeset.html#usage-basics>`_
  `NodeSet` syntax is also supported.

* **match** expects a valid regular expression

* **tags** expects a list of tag names

* **constraint** expects a string. This tag does not references node
  names explicitely but instead delegates it to SLURM. The value of the
  constraint tag is given to the sbatch options through the
  *--constraint* option.

cluster
~~~~~~~
If value is "slurm", then the network ``nodes`` is filled based on the output
of the ``info`` command. A tag will be also added for every
(partition, feature) tuple formatted like this: ``{partition}_{feature}``.

slurm_blacklist_states
~~~~~~~~~~~~~~~~~~~~~~
List of SLURM node states used to filter-out nodes when ``cluster`` option
is set to ``slurm``. Default states are down, drained, draining, error,
fail, failing, future, maint, and reserved.

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
* ``git+http://github.com/BlueBrain/hpcbench@master#egg=hpcbench`` to install the bleeding edge version.
* ``git+http://github.com/me/hpcbench@feat/awesome-feature#egg=hpcbench`` to deploy a fork's branch.

Benchmarks configuration reference
----------------------------------

The **benchmarks** section specifies benchmarks to execute
on every tag.

* key: the tag name or `"*"`. `"*"` matches all nodes described
  in the *network.nodes* section.
* value: a dictionary of name -> benchmark description.

.. code-block:: yaml

  benchmarks:
    cpu:
      test_cpu:
        type: sysbench
    '*':
      check_ram
        type: random_ram_rw

Tag specific sbatch parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When running in :ref:`SLURM mode<process-type>` a special `sbatch` dictionary can be used.
This dictionary will be used when generating the sbatch file specific to this tag, allowing
parameters to be overwritten.

.. code-block:: yaml
  :emphasize-lines: 9-11

  process:
    type: slurm
    sbatch:
      time: 01:00:00
      tasks-per-node: 1

  benchmarks:
    cpu:
      sbatch:
        hint: compute_bound
        tasks-per-node: 16
      test_cpu:
        type: sysbench

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
override default behavior, which is defined in the benchmark class.

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

srun (optional)
~~~~~~~~~~~~~~~

When hpcbench is run in `srun` or `slurm` benchmark execution mode, this key roots a list of
options, which are passed to the `srun` command. Note that only the long form
option names should be used (i.e. `--nodes` instead of `-N`). These options overwrite
the global options provided in the :ref:`process <campaign-process>` section. To disable
a global srun option simply declare the option without providing a value. if an option without
value (e.g. `--exclusvie`) is to be used in `srun`, the key should be assigned to `true`.

.. code-block:: yaml
  :emphasize-lines: 4,7,8

  benchmarks:
    cpu:
      osu:
        srun:
          nodes: 8
          ntasks-per-node: 36
          hint:
          exclusive: true
        type: osu

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

All executions are present in the report but only metrics of the last run are reported. The
``sorted`` key allows to change this behavior to reorder the runs according to criterias.

.. code-block:: yaml
  :emphasize-lines: 6-8

  benchmarks:
      '*':
          test01:
              type: imb
              attempts:
                  fixed: 5
                  sorted:
                    sql: metrics__latency
                    reverse: true

``sql`` can be a string or a list of string in kwargsql format. They are used to
sort hpcbench.yaml reports. ``reverse`` is optional and allows to reverse the sort order.
In this example, the report with the smallest latency is picked.

The dynamic way allows you to execute the same command over and over again
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
they are not converted to python True or False values by the YAML parse.
If specified, this section supersedes environment variables
emitted by benchmark.

.. code-block:: yaml
  :emphasize-lines: 5

  benchmarks:
    '*':
      test_cpu:
        type: sysbench
        environment:
          TEST_ALL: 'true'
          LD_LIBRARY_PATH: /usr/local/lib64

modules (optional)
~~~~~~~~~~~~~~~~~~
List of modules to load before executing the command.
If specified, this section supersedes modules emitted by benchmark.

cwd (optional)
~~~~~~~~~~~~~~
Specifies a custom working directory.

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
  variable to be defined for being executed.
* **cpu_numactl_1** benchmark needs either ``HPCBENCH_MCDRAM`` or
  ``HPCBENCH_CACHE`` environment variables to defined for being executed.
*  **disk** benchmark will be executed in all cases.

.. _campaign-process:

Process configuration reference
-------------------------------
This section specifies how ``ben-sh`` execute the benchmark commands.


.. _process-type:

type (optional)
~~~~~~~~~~~~~~~
A string indicating the execution layer. Possible values are:

* ``local`` (default) directs HPCbench to spawn child processes where ``ben-sh``
  is running.
* ``slurm`` will use `SLURM <https://slurm.schedmd.com>`_ mode. This will cause HPCBench
  to generate for each tag in the network, which is used by at least one benchmark, one **sbatch**
  file. The batch file is then submitted to the scheduler. By default this batch file will invoke
  hpcbench on the allocated nodes and execute the benchmarks for this tag.
* ``srun`` will use `srun <https://slurm.schedmd.com/srun.html>`_ to launch the benchmark
  processes. When HPCBench is being executed inside the self-generated batch script, it will
  use by default the ``srun`` mode to run the benchmarks.

commands (optional)
~~~~~~~~~~~~~~~~~~~

This dictionary allows setting alternative `srun` or `sbatch` commands or absolute paths to
the binaries.

.. code-block:: yaml
  :emphasize-lines: 3

  process:
    type: slurm
    commands:
      sbatch: /opt/slurm/bin/sbatch
      srun: /opt/slrum/bin/sbatch

srun and sbatch (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``srun`` and ``sbatch`` dictionaries provide configurations foe the respective SLURM
commands.


.. code-block:: yaml

  process:
    type: slurm
    sbatch:
      account: users
      partition: über-cluster
      mail-type: ALL
    srun:
      mpi: pmi2

executor_template (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Override default Jinja template used to generate
shell-scripts in charge of executing benchmarks.
Default value is:

.. code-block:: shell

  #!/bin/sh
  {%- for var, value in environment.items() %}
  export {{ var }}={{ value }}
  {%- endfor %}
  cd "{{ cwd }}"
  exec {{ " ".join(command) }}

If value does not start with shebang, then it is considered
like a file location.

Global metas dictionary (optional)
----------------------------------
If present at top-level of YAML file, content  of ``metas`` dictionary
will be merged with those from every execution (see
``hpcbench.api.Benchmark.execution_context``)
Those defined in ``execution_context`` take precedence.

Environment variable expansion
------------------------------

Your configuration options can contain environment variables. HPCBench uses the
variable values from the shell environment in which `ben-sh` is run.
For example, suppose the shell contains EMAIL=root@cscs.ch and you supply this configuration:

.. code-block:: yaml

  process:
    type: slurm
    sbatch:
      email=$EMAIL
      partition=über-cluster


When you run ben-sh with this configuration, HPCBench will look for the EMAIL
environment variable in the shell and substitutes its value in.

If an environment variable is not set, substitution fails and an exception is raised.

Both $VARIABLE and ${VARIABLE} syntax are supported. Additionally, it is possible
to provide inline default values using typical shell syntax:

${VARIABLE:-default} will evaluate to default if VARIABLE is unset or empty in the environment.
${VARIABLE-default} will evaluate to default only if VARIABLE is unset in the environment.
${#VARIABLE} will evaluate to the length of the environment variable.
Other extended shell-style features, such as ${VARIABLE/foo/bar}, are not supported.

You can use a $$ (double-dollar sign) when your configuration needs a literal dollar sign.
This also prevents HPCBench from interpolating a value, so a $$ allows you to
refer to environment variables that you don’t want processed by HPCBench.

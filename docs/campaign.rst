HPCBench Campaign file reference
================================

HPCBench uses a YAML file
(see `YAML cookbook <http://yaml.org/YAML_for_ruby.html>`_)
to describe a tests campaign.
Topics of this reference page are organized by top-level key
to reflect the structure of the Campaign file itself.

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

* **nodes** expects an exaustive list of nodes.
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
      options:
        - --account=project42
        - --partition=über-cluster

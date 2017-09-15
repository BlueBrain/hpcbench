 #!/bin/bash

LOCAL_PATH=$PWD
#to define
GPFS_PATH=/gpfs/bbp.cscs.ch/project/proj16/

function check {
    if [ $? -eq 0 ]; then
        echo $1 $2 OK
    else
        echo $1 $2 OK
    fi
}

function basic {
    mkdir test  > /dev/null 2>&1
    check $1 mkdir
    cd test  > /dev/null 2>&1
    check $1 cd
    > test.txt  > /dev/null 2>&1
    check $1 \>
    find test.txt > /dev/null 2>&1
    check $1 find
    echo "Hello BBP5." > test.txt
    check $1 echo
    grep "Hello" test.txt > /dev/null 2>&1
    check $1 grep
    mv test.txt rename.txt  > /dev/null 2>&1
    check $1 mv
    cp rename.txt rename1.txt  > /dev/null 2>&1
    check $1 cp
    rm rename.txt rename1.txt  > /dev/null 2>&1
    check $1 rm
    cd ..  > /dev/null 2>&1
    rm -r test  > /dev/null 2>&1
}

function local_read_write {
    cd $LOCAL_PATH
    basic fs_local
}

function gpfs_read_write {
    cd $GPFS_PATH
    basic fs_gpfs
}

function hello_word_setup {
    cd $LOCAL
    mkdir hello
    cd hello
}

function hello_word_clean {
    cd $LOCAL
    rm -rf hello
}

function hello_word_file {
cat <<EOM >main.c
#include <stdio.h>
#include "mpi.h"
#include <omp.h>

int main(int argc, char *argv[]) {
  int numprocs, rank, namelen;
  char processor_name[MPI_MAX_PROCESSOR_NAME];
  int iam = 0, np = 1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &numprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Get_processor_name(processor_name, &namelen);

  #pragma omp parallel default(shared) private(iam, np)
  {
    np = omp_get_num_threads();
    iam = omp_get_thread_num();
    printf("Hello from thread %d out of %d from process %d out of %d on %s\n",
           iam, np, rank, numprocs, processor_name);
  }

  MPI_Finalize();
}
EOM
}

function hello_word_compilation {
    mpicc -fopenmp main.c -o hello_word > /dev/null 2>&1
    check hello compilation
}

function hello_word_execution {
    mpirun -n 2 ./hello_word > /dev/null 2>&1
    check hello execution
}

function ping_allnodes {
    cat $LOCAL_PATH/list_ip.txt | while read output
    do
        ping -c 1 "$output" > /dev/null
        check in_network "ping $output"
    done
}

function ping_test {
    #200 bytes website, fastest of the world
    #3 seconds wait else error
    ping -c 1 www.perdu.com > /dev/null 2>&1
    check out_network ping
}

function wget_test {
    #200 bytes website, fastest of the world
    #3 seconds wait else error
    wget -T 3 www.perdu.com > /dev/null 2>&1
    check out_network wget
    rm -f index.html
}

local_read_write
gpfs_read_write
ping_test
wget_test
hello_word_setup
hello_word_file
hello_word_compilation
hello_word_execution
hello_word_clean
ping_allnodes

#!/bin/bash

RUN_PATH="$PWD"
LOCAL_PATH="${LOCAL_PATH:-$PWD}"
NETWORK_PATH="${NETWORK_PATH:-/gpfs/bbp.cscs.ch/project/proj16/}"

# URL behind proxy
# 200 bytes website, fastest of the world
OUTSIDE_URL="${OUTSIDE_URL:-www.perdu.com}"

INSIDE_URL="${INSIDE_URL:-}"

check() {
    if [ $? -eq 0 ]; then
        echo "$1" "$2" OK
    else
        echo "$1" "$2" KO
    fi
}

basic() {
    mkdir test >&2
    check "$1" mkdir
    cd test >&2
    check "$1" cd
    touch test.txt >&2
    check "$1" touch
    find test.txt >&2
    check "$1" find
    echo "Hello BB5." > test.txt
    check "$1" write
    grep "Hello" test.txt >&2
    check "$1" grep
    mv test.txt rename.txt >&2
    check "$1" mv
    cp rename.txt rename1.txt >&2
    check "$1" cp
    rm rename.txt rename1.txt >&2
    check "$1" rm
    cd .. >&2
    rm -r test >&2
}

local_read_write() {
    cd "$LOCAL_PATH"
    basic fs_local
}

gpfs_read_write() {
    cd "$NETWORK_PATH"
    basic fs_network
}

hello_word_setup() {
    cd "$LOCAL_PATH"
    mkdir hello
    cd hello
}

hello_word_clean() {
    cd "$LOCAL_PATH"
    rm -rf hello
}

hello_word_file() {
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

hello_word_compilation() {
    mpicc -fopenmp main.c -o hello_word >&2
    check hello_world compilation
}

hello_word_execution() {
    mpirun -n 2 ./hello_word >&2
    check hello_world execution
}

ping_allnodes() {
    if [ "x$PING_IPS" = x ] ; then
      echo "Skip nodes ping test because PING_IPS is undefined" >&2
      return
    fi
    if ! [ -f "$RUN_PATH/$PING_IPS" ] ; then
      echo "Skip nodes ping test because $RUN_PATH/$PING_IPS does not exist" >&2
      return
    fi
    result=0
    while read ip; do
        ping -c 1 "$ip" >&2
        result=$((result + $?))
    done <"$RUN_PATH/PING_IPS"
    [ $result -eq 0 ]
    check in_network "ping"
}

ping_test() {
    if [ "x$2" = x ] ; then
      echo "Skip $1_network ping test because URL not set" >&2
      return 0
    fi
    #3 seconds wait else error
    ping -c 1 "$2" >&2
    check "$1_network" ping
}

wget_test() {
    if [ "x$2" = x ] ; then
      echo "Skip $1_network wget test because URL not set" >&2
      return 0
    fi
    wget -T 3 "$2" >&2
    check "$1_network" wget
    rm -f index.html
}

local_read_write
gpfs_read_write
ping_test inside "$INSIDE_URL"
wget_test inside "$INSIDE_URL"
ping_test outside "$OUTSIDE_URL"
wget_test outside "$OUTSIDE_URL"
hello_word_setup
hello_word_file
hello_word_compilation
hello_word_execution
hello_word_clean
ping_allnodes

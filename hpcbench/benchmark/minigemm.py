"""Test basic functionality of BB5
"""
from __future__ import print_function

import os.path as osp

import subprocess

import os
import stat
from cached_property import cached_property

from hpcbench.api import (
    Benchmark,
    Metrics,
    MetricsExtractor,
    Metric)


class BasicExtractor(MetricsExtractor):

    METRICS = dict(
        time=Metrics.Second,
        gflops=Metrics.GFlops,
        checksum=Metric('#',float)
    )
    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self.METRICS

    def extract_metrics(self, outdir, metas):
        # parse stdout and extract desired metrics
        with open(self.stdout(outdir)) as istr:
            timel = istr.readline()
            time = float(timel.split()[-1][:-1])
            flopl = istr.readline()
            gflops = float(flopl.split()[0])
            checkl = istr.readline()
            chk = float(checkl.split()[-1])
        metrics = dict(
            time=time,
            gflops=gflops,
            checksum=chk
        )
        return metrics

SOURCE = """#include <iostream>
#include <chrono>
#include "mkl.h"
#include "omp.h"

#define fix_lda(x)   (((x + 255) & ~255) + 16)
#define min(x,y) (((x) < (y)) ? (x) : (y))

#define ALPHA 1.0
#define BETA 1.0
#define NITER 100
#define DIM_M 8000
#define DIM_K 4096
#define DIM_N 4096

int main(int argc, char **argv) {
  double alpha, beta;
  int m, n, k;
  int niter = NITER;
  int nthreads = omp_get_max_threads();
#ifdef DBG_PRINT
  std::cout << "Running with " << nthreads << " outer threads\\n";
#endif
  alpha = ALPHA;
  beta = BETA;
  m = DIM_M;
  k = fix_lda(DIM_K);
  n = fix_lda(DIM_N);

  omp_set_max_active_levels(2);

  double gflop = (2.0*m*k*n)*1e-9*niter*nthreads;

  auto As = (double**)malloc(nthreads*sizeof(double*));
  auto Bs = (double**)malloc(nthreads*sizeof(double*));
  auto Cs = (double**)malloc(nthreads*sizeof(double*));

  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    auto A = (double*)mkl_malloc(m*k*sizeof(double), 64);
    auto B = (double*)mkl_malloc(k*n*sizeof(double), 64);
    auto C = (double*)mkl_malloc(m*n*sizeof(double), 64);
    if ((A == NULL) || (B == NULL) || (C == NULL)) {
      mkl_free(A);
      mkl_free(B);
      mkl_free(C);
      return 1;
    }
    As[ithrd] = A;
    Bs[ithrd] = B;
    Cs[ithrd] = C;
  }

  #pragma omp parallel for schedule(static,1) num_threads(nthreads)
  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    auto A = As[ithrd];
    auto B = Bs[ithrd];
    auto C = Cs[ithrd];
    for(int i = 0; i < m*k; ++i) {
      A[i] = 1.1*(i+1);
    }
    for(int i = 0; i < k*n; ++i) {
      B[i] = 1.2*(i+2);
    }
    for(int i = 0; i < m*n; ++i) {
      C[i] = 0.0;
    }
  }

  #pragma omp parallel for schedule(static, 1) num_threads(nthreads)
  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                m, n, k, alpha, As[ithrd], k, Bs[ithrd], n, beta, Cs[ithrd], n);
  }

  auto tstart = std::chrono::high_resolution_clock::now();
  #pragma omp parallel for schedule(static, 1) num_threads(nthreads)
  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    for (int iter = 0; iter < niter; iter++) {
      cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                  m, n, k, alpha, As[ithrd], k, Bs[ithrd], n, beta, Cs[ithrd], n);
    }
  }
  auto tend = std::chrono::high_resolution_clock::now();

  std::chrono::duration<double> tdiff = tend - tstart;
  std::cout << "Time elapsed for " << niter << " iterations: " << tdiff.count() << "s\\n";
  std::cout << gflop/tdiff.count() << " GFLOP/s\\n";

#ifdef DBG_PRINT
  for(int i = 0; i < min(m, 5); ++i) {
    for(int j = 0; j < min(n, 5); ++j) {
      std::cout << Cs[0][j + i*n] << "  ";
    }
    std::cout << std::endl;
  }
#endif

  double chk;
  double sgn = 1.0;
  for(int j = 0; j < nthreads; j++) {
    for(int i = 0; i < m*n; ++i) {
      sgn *= -1.0;
      chk += sgn*Cs[j][i];
    }
  }
  std::cout << "Check value: " << chk << std::endl;

  for(int j = 0; j < 2; j++) {
    mkl_free(As[j]);
    mkl_free(Bs[j]);
    mkl_free(Cs[j]);
  }
  free(As);
  free(Bs);
  free(Cs);

  return 0;
}
"""

COMPILE_SCRIPT = """#!/bin/bash -l
module load intel-mkl
g++ {defines} -O3 -std=c++11 -fopenmp  -m64 -I${{MKLROOT}}/include  \
    -L${{MKLROOT}}/lib/intel64 -Wl,--no-as-needed -lmkl_intel_lp64 \
    -lmkl_gnu_thread -lmkl_core -lgomp -lpthread -lm -ldl \
    -o minigemm minigemm.cpp

"""


class MiniGEMM(Benchmark):
    """A mini benchmark performing MKL based generalized matrix multiplies
    to determine the node's peak floating point performance.
    """
    name = 'minigemm'
    description = "DGEMM mini benchmark"
    COMPILE_PARAMS = dict(
        defines=dict(
    ))

    def __init__(self):
        super(MiniGEMM, self).__init__(
            attributes=dict(
            theoretical_peak="",
            compile=self.COMPILE_PARAMS
        ))


    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category=self.name,
            command=['./minigemm'],
            environment=dict(
                MKL_DYNAMIC='false',
                OMP_NESTED='true',
                OMP_PROC_BIND='spread,close',
                OMP_NUM_THREADS='1',
                MKL_NUM_THREADS='4',
            ),
        )

    def _compile(self, execution):
        with open('minigemm.cpp', 'w') as ostr:
            print(SOURCE, file=ostr)
        defines = []
        for name,val in self.attributes['compile']['defines'].items():
            if val is None:
                defines.append('-D{}'.format(name))
            else:
                defines.append('-D{}={}'.format(name, val))
        define_str = ' '.join(defines)
        with open('compile.sh','w') as ostr:
            print(COMPILE_SCRIPT.format(defines=define_str), file=ostr)
        st = os.stat('compile.sh')
        os.chmod('compile.sh', st.st_mode | stat.S_IEXEC)
        proc = subprocess.run(['./compile.sh'],
                              stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                              shell=True)
        print(proc.stdout)
        print(proc.stderr)


    def pre_execute(self, execution):
        self._compile(execution)

    @cached_property
    def metrics_extractors(self):
        return BasicExtractor()


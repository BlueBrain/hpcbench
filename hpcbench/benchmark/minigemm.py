"""Test basic functionality of BB5
"""
from __future__ import print_function

import os
import stat
import subprocess

from cached_property import cached_property

from hpcbench.api import Benchmark, Metric, Metrics, MetricsExtractor


class GemmExtractor(MetricsExtractor):

    METRICS = dict(
        time=Metrics.Second, gflops=Metrics.GFlops, checksum=Metric('#', float)
    )

    @property
    def metrics(self):
        """ The metrics to be extracted.
            This property can not be replaced, but can be mutated as required
        """
        return self.METRICS

    def extract_metrics(self, metas):
        # parse stdout and extract desired metrics
        with open(self.stdout) as istr:
            timel = istr.readline()
            time = float(timel.split()[-1][:-1])
            flopl = istr.readline()
            gflops = float(flopl.split()[0])
            checkl = istr.readline()
            chk = float(checkl.split()[-1])
        metrics = dict(time=time, gflops=gflops, checksum=chk)
        return metrics


SOURCE = """#include <iostream>
#include <chrono>
#include "mkl.h"
#include "omp.h"

#define fix_lda(x)   (((x + 255) & ~255) + 16)
#define min(x,y) (((x) < (y)) ? (x) : (y))

#define ALPHA 1.0
#define BETA 1.0
#define NITER 20
#ifndef DIM_M
#define DIM_M 8000
#endif
#ifndef DIM_K
#define DIM_K 4096
#endif
#ifndef DIM_N
#define DIM_N 4096
#endif

int main(int argc, char **argv) {
  double alpha, beta;
  size_t m, n, k;
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

  double gflop = (m*n*(2*k+2))*1e-9*niter*nthreads;

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
    for(size_t i = 0; i < m*k; ++i) {
      A[i] = 1.1*(i+1);
    }
    for(size_t i = 0; i < k*n; ++i) {
      B[i] = 1.2*(i+2);
    }
    for(size_t i = 0; i < m*n; ++i) {
      C[i] = 0.0;
    }
  }

  #pragma omp parallel for schedule(static, 1) num_threads(nthreads)
  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                m, n, k, alpha, As[ithrd], k, Bs[ithrd], n,
                beta, Cs[ithrd], n);
  }

  auto tstart = std::chrono::high_resolution_clock::now();
  #pragma omp parallel for schedule(static, 1) num_threads(nthreads)
  for (int ithrd = 0; ithrd < nthreads; ithrd++) {
    for (int iter = 0; iter < niter; iter++) {
      cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                  m, n, k, alpha, As[ithrd], k, Bs[ithrd], n,
                  beta, Cs[ithrd], n);
    }
  }
  auto tend = std::chrono::high_resolution_clock::now();

  std::chrono::duration<double> tdiff = tend - tstart;
  std::cout << "Time elapsed for " << niter << " iterations: "
            << tdiff.count() << "s\\n";
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
  for(int ithrd = 0; ithrd < nthreads; ithrd++) {
    for(int i = 0; i < m*n; ++i) {
      sgn *= -1.0;
      chk += sgn*Cs[ithrd][i];
    }
  }
  std::cout << "Check value: " << chk << std::endl;

  for(int ithrd = 0; ithrd < nthreads; ithrd++) {
    mkl_free(As[ithrd]);
    mkl_free(Bs[ithrd]);
    mkl_free(Cs[ithrd]);
  }
  free(As);
  free(Bs);
  free(Cs);

  return 0;
}
"""

COMPILE_SCRIPT = """#!/bin/bash -l
make DEFINES="{opts}"
"""

MAKEFILE = """CXX=icpc
DEFINES=
CXXFLAGS=-qopt-streaming-stores always -O3 -mkl -std=c++11 -qopenmp
LDFLAGS=

CPPFILES=minigemm.cpp
OBJ=$(CPPFILES:.cpp=.o)

all: minigemm

.cpp.o: $<
    $(CXX) -c $< $(DEFINES) $(CXXFLAGS)

minigemm: $(OBJ)
    $(CXX) -o $@ $^ $(CXXFLAGS) $(LDFLAGS)

clean:
    $(RM) minigemm *.o

.PHONY: clean

"""


class MiniGEMM(Benchmark):
    """DGEMM mini benchmark

    A mini benchmark performing MKL based generalized matrix multiplies
    to determine the node's peak floating point performance.
    """

    name = 'minigemm'
    COMPILE_PARAMS = []
    DEFAULT_OPENMP_THREADS = 1
    DEFAULT_NESTED_MKL_THREADS = 4

    def __init__(self):
        super(MiniGEMM, self).__init__(
            attributes=dict(
                compile=self.COMPILE_PARAMS,
                omp_threads=self.DEFAULT_OPENMP_THREADS,
                mkl_threads=self.DEFAULT_NESTED_MKL_THREADS,
            )
        )

    @cached_property
    def compile(self):
        """Add user defined compiler options
        """
        return self.attributes['compile']

    @cached_property
    def omp_threads(self):
        """Set the number of OpenMP threads used,
        typically equals the number of NUMA domains
        """
        return str(self.attributes['omp_threads'])

    @cached_property
    def mkl_threads(self):
        """Set the number of MKL threads used,
        typically equals the number of cores per NUMA domain
        """
        return str(self.attributes['mkl_threads'])

    def execution_matrix(self, context):
        del context  # unused
        yield dict(
            category=self.name,
            command=['./minigemm'],
            environment=dict(
                MKL_DYNAMIC='false',
                OMP_NESTED='true',
                OMP_PROC_BIND='spread,close',
                OMP_PLACES='cores',
                OMP_NUM_THREADS=','.join([self.omp_threads, self.mkl_threads]),
            ),
        )

    def _compile(self, execution, context):
        with open('minigemm.cpp', 'w') as ostr:
            print(SOURCE, file=ostr)
        with open('Makefile', 'w') as ostr:
            print(MAKEFILE.replace('    ', '\t'), file=ostr)
        opt_str = ' '.join(self.compile)
        with open('compile.sh', 'w') as ostr:
            print(COMPILE_SCRIPT.format(opts=opt_str), file=ostr)
        st = os.stat('compile.sh')
        os.chmod('compile.sh', st.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call(['./compile.sh'])
        except subprocess.CalledProcessError as cpe:
            context.logger.warning(
                'minigemm compilation failed, error code:', cpe.returncode
            )
        else:
            context.logger.info('Successfully compiled minigemm benchmark')

    def pre_execute(self, execution, context):
        self._compile(execution, context)

    @cached_property
    def metrics_extractors(self):
        return GemmExtractor()

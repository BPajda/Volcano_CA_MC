// Punkt wejścia testów MPI (etap 10): doctest w każdym procesie, ten sam porządek testów (te same wywołania zbiorowe).
// Wynik porównuje proces 0 i rozsyła go do pozostałych; proces inny niż 0 wypisuje tylko błędy (--minimal).
// Kod wyjścia: maksimum po procesach (mpiexec zgłosi błąd, jeśli test nie przeszedł na którymkolwiek).
#define DOCTEST_CONFIG_IMPLEMENT
#include "doctest.h"

#include <mpi.h>

int main(int argc, char** argv) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    doctest::Context ctx(argc, argv);
    if (rank != 0) {
        ctx.setOption("minimal", true);
    }
    int result = ctx.run();
    MPI_Allreduce(MPI_IN_PLACE, &result, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    MPI_Finalize();
    return result;
}

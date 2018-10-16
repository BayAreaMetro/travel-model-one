/* Convert binary matrices to the TP+ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "binaryToTpp.h"

void main(int argc, char *argv[]) {
	char *tpplus;
	char **binary;

	if (argc < 3) {
		printf("usage: covertBinaryTpplus <tpplus matrix file> <binary file1>...\n");
		fflush(stdout);
		exit(-2);
	}

	tpplus = argv[1];
	binary = argv;
	printf("binary %s\n", *binary);
	printf("binary %s\n", *(++binary));
	printf("binary %s\n", *(++binary));

	tppInitDllNative();
	combineBinaryTablesInTpplusFile(binary, tpplus, argc - 2);
}

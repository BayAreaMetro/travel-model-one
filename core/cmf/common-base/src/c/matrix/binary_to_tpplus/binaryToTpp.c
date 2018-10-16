#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "binaryToTpp.h"

#define bigToLittle(A)  ( ( ((unsigned long)(A) & 0xff000000) >> 24 ) | ( ((unsigned long)(A) & 0x00ff0000) >>  8 ) | ( ((unsigned long)(A) & 0x0000ff00) <<  8 ) | ( ((unsigned long)(A) & 0x000000ff) << 24 ) )
#define bigToLittleShort(A) ( ( ((unsigned short)(A) & 0xff00) >>  8 ) | ( ((unsigned short)(A) & 0x00ff) << 8 ) )

void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables) {

	int tppWrite (char *fileName, double *MatrixOP, int nzones, int ntables);
	int tppWriteWithNames (char *fileName, double *MatrixOP, int nzones, int ntables, char** matName);
	int tppClose ();


	/*int dummy=0;*/
	
	FILE **fpIn;
	int i, j, k, m;
	int tempInt;
	short tempShort;
	short length;
	float *tempRow;
	unsigned long int *tempPointer;
	double *matrixUnrolled;
	double *tableTotals;
	char **names;
	

	struct hdr {
		int version;
		int nRows;
		int nCols;
		int nExternalRowLabels;
		int nExternalColLabels;
		char *name;
		char *description;
		int *externalRowLabels;
		int *externalColLabels;
	};
	struct hdr *headers;




	// allocate memory for array of file pointers
	fpIn = (FILE **) calloc (ntables, sizeof(FILE *));

	// allocate memory for array of header data structures
	headers = (struct hdr *) calloc (ntables, sizeof(struct hdr));
	names = (char **) calloc(ntables, sizeof(char*));

	// opening binary tables written out by BinaryMatrixWriter.java.
	// read headers in each file as well.
	for (i=0; i < ntables; i++) {
		printf("About to open %s.\n", binaryFileNames[i]);

		if ( (fpIn[i] = fopen(binaryFileNames[i], "rb")) == NULL ) {
			printf ("error opening binary trip table %d of %d tables, named %s for reading.\n", i+1, ntables, binaryFileNames[i]);
			fflush (stdout);
			exit (-1);
		}

		// the values in the binary matrix were written in big_endian by java and need to be converted to little_endian.
		
		//version
		fread (&tempInt, sizeof(int), 1, fpIn[i]);
		headers[i].version = bigToLittle (tempInt);

		//number of rows
		fread (&tempInt, sizeof(int), 1, fpIn[i]);
		headers[i].nRows = bigToLittle (tempInt);

		//number of cols
		fread (&tempInt, sizeof(int), 1, fpIn[i]);
		headers[i].nCols = bigToLittle (tempInt);

		//number of external row labels
		fread (&tempInt, sizeof(int), 1, fpIn[i]);
		headers[i].nExternalRowLabels = bigToLittle (tempInt);

		//number of external col labels
		if(headers[i].version == 2){
			fread (&tempInt, sizeof(int), 1, fpIn[i]);
			headers[i].nExternalColLabels = bigToLittle (tempInt);
		}else{
			headers[i].nExternalColLabels = headers[i].nExternalRowLabels;
		}
		//name
		fread (&length, sizeof(short), 1, fpIn[i]);
		length = bigToLittleShort(length);

		headers[i].name = (char *) calloc (length+1, sizeof(char));
		for (j=0; j < length; j++) {
			fread (&tempShort, sizeof(char), 1, fpIn[i]);
			headers[i].name[j] = (char)tempShort;
		}
		headers[i].name[length] = '\0';
		names[i] =  headers[i].name;
		
		//description
		fread (&length, sizeof(short), 1, fpIn[i]);
		length = bigToLittleShort(length);

		headers[i].description = (char *) calloc (length+1, sizeof(char));

		for (j=0; j < length; j++) {
			fread (&tempShort, sizeof(char), 1, fpIn[i]);
			headers[i].description[j] = (char)tempShort;
		}
		headers[i].description[length] = '\0';
		
		//external row labels
		headers[i].externalRowLabels = (int *) calloc (headers[i].nExternalRowLabels, sizeof(int));
		for (j=1; j < headers[i].nExternalRowLabels; j++) {
			fread (&tempInt, sizeof(int), 1, fpIn[i]);
			headers[i].externalRowLabels[j] = bigToLittle (tempInt);
		}

		//external col labels
		if(headers[i].version == 2){
			headers[i].externalColLabels = (int *) calloc (headers[i].nExternalColLabels, sizeof(int));
			for (j=1; j < headers[i].nExternalColLabels; j++) {
				fread (&tempInt, sizeof(int), 1, fpIn[i]);
				headers[i].externalColLabels[j] = bigToLittle (tempInt);
			}
		}else{
			headers[i].externalColLabels = (int *) calloc (headers[i].nExternalColLabels, sizeof(int));
			for (j=1; j < headers[i].nExternalColLabels; j++) {
				headers[i].externalColLabels[j] = headers[i].externalRowLabels[j];
			}
			
		}
		printf ("table %d of %d named %s opened for reading.\n", i+1, ntables, binaryFileNames[i]);
		printf ("name=%s, description=%s, nrows=%d, ncols=%d, nRowLabels=%d, nColLabels=%d.\n\n", headers[i].name, 
			headers[i].description, headers[i].nRows, headers[i].nCols, headers[i].nExternalRowLabels, headers[i].nExternalColLabels);

	}

	tableTotals = (double *) calloc (ntables, sizeof(double));
	tempRow = (float *) calloc (sizeof(float), headers[0].nRows);
	matrixUnrolled = (double *) calloc (headers[0].nRows*ntables*headers[0].nCols, sizeof(double));

	k = 0;
	for (i=0; i < headers[0].nRows; i++) {
		for (m=0; m < ntables; m++) {
			fread (tempRow, sizeof(float), headers[m].nCols, fpIn[m]);
			for (j=0; j < headers[m].nCols; j++) {
				tempPointer = (unsigned long int *) &tempRow[j];
				*tempPointer = bigToLittle(*tempPointer);
				matrixUnrolled[k] = *((float *)tempPointer);
				tableTotals[m] += matrixUnrolled[k];
				k++;
			}
		}
	}
			
	printf("About to call tppWrite.\n");
	tppWriteWithNames (tppFileName, matrixUnrolled, headers[0].nRows, ntables,names);
	for (i=0; i < ntables; i++)
		printf ("table %d of %d values total to %.2f.\n", i+1, ntables, tableTotals[i]);


	free (tableTotals);
	free (tempRow);
	free (matrixUnrolled);

}



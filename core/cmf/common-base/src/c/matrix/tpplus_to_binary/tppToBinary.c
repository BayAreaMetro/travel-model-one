#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define littleToBig(A)  ( ( ((unsigned long)(A) & 0xff000000) >> 24 ) | ( ((unsigned long)(A) & 0x00ff0000) >>  8 ) | ( ((unsigned long)(A) & 0x0000ff00) <<  8 ) | ( ((unsigned long)(A) & 0x000000ff) << 24 ) )


void splitTpplusTablesIntoBinaryFiles (char *tppFileName, char *tpplusFilesDirectory, char *binaryFilesDirectory) {

	void tppReadSeq (char *inputFilename, double *MatrixIP);
	int tppGetNumberOfTables (char *inputFilename);
	int tppGetNumberOfRows (char *inputFilename);
	int tppClose ();


	
	FILE **fpOut;

	char **binaryFileNames;
	char tempName[1024];
	char fullTppFileName[1024];

	int i, j, k, m;
	int nRows;
	int nTables;
	int tempInt;
	short tempShort;
	float *tempRow;
	unsigned long int *tempPointer;
	double *matrixUnrolled;

	
	strcpy (tempName, tpplusFilesDirectory);
	strcat (tempName, "\\");
	strcat (tempName, tppFileName);
	strcpy (fullTppFileName, tempName);


	// find out number of tables and rows in tpplus matrix file and allocate array for reading matrix data
	nTables = tppGetNumberOfTables (fullTppFileName);
	nRows = tppGetNumberOfRows (fullTppFileName);

	matrixUnrolled = (double *) calloc (nRows*nRows*nTables, sizeof(double));




	// allocate memory for array of file pointers
	fpOut = (FILE **) calloc (nTables, sizeof(FILE *));
	binaryFileNames = (char **) calloc (nTables, sizeof(char *));


	// opening binary tables to be written out so they can be read by BinaryMatrixReader.java.
	// write headers in each file as well.
	for (i=0; i < nTables; i++) {

		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));

		// replace the extension at the end of the tpplus filename with xx.binary, where xx is the table number.
		strcpy (tempName, binaryFilesDirectory);
		strcat (tempName, "\\");
		strcat (tempName, tppFileName);
		j = strlen(tempName);
		while (tempName[j] != '.') {
			j--;
		}
		sprintf(&tempName[j], "%i.binary", i+1);
		if (i < 10)
			tempName[j+8+1] = '\0';
		else if (i < 100)
			tempName[j+9+1] = '\0';
		else if (i < 1000)
			tempName[j+10+1] = '\0';
		else if (i < 10000)
			tempName[j+11+1] = '\0';

		strcpy (binaryFileNames[i], tempName);



		if ( (fpOut[i] = fopen(binaryFileNames[i], "wb")) == NULL ) {
			printf ("error opening binary table %d of %d tables, named %s for writing.\n", i+1, nTables, binaryFileNames[i]);
			fflush (stdout);
			exit (-1);
		}


		// the values in the binary matrix are read as big_endian by java and thus need to be so converted.
		tempInt = littleToBig(1);
		fwrite (&tempInt, sizeof(int), 1, fpOut[i]);

		tempInt = littleToBig(nRows);
		fwrite (&tempInt, sizeof(int), 1, fpOut[i]);

		tempInt = littleToBig(nRows);
		fwrite (&tempInt, sizeof(int), 1, fpOut[i]);

		tempInt = littleToBig(nRows+1);
		fwrite (&tempInt, sizeof(int), 1, fpOut[i]);

		tempShort = littleToBig(0);
		fwrite (&tempInt, sizeof(short), 1, fpOut[i]);

		tempShort = littleToBig(0);
		fwrite (&tempInt, sizeof(short), 1, fpOut[i]);

		for (j=1; j < nRows+1; j++) {
			tempInt = littleToBig(j);
			fwrite (&tempInt, sizeof(int), 1, fpOut[i]);
		}


		printf ("table %d of %d named %s opened for writing.\n", i+1, nTables, binaryFileNames[i]);

	}





	// call the dll funcrion to read the matrix data into this array
	tppReadSeq (fullTppFileName, matrixUnrolled);



	// allocate a work array for writing biary data
	tempRow = (float *) calloc (sizeof(float), nRows);



	// copy matrix data to the work array and convert values to BIG_ENDIAN for writing to BinaryMatrixData file format
	k = 0;
	for (i=0; i < nRows; i++) {
		for (m=0; m < nTables; m++) {
			for (j=0; j < nRows; j++) {
				tempRow[j] = (float)matrixUnrolled[k];
				tempPointer = (unsigned long int *) &tempRow[j];
				*tempPointer = littleToBig(*tempPointer);
				matrixUnrolled[k] = *((float *)tempPointer);
				k++;
			}
			fwrite (tempRow, sizeof(float), nRows, fpOut[m]);
		}
	}
			


	free (tempRow);
	free (matrixUnrolled);

}



/* Convert highway binary matrices to the TP+ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


void convert_man_nonmotoram (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);




	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_nonmotor_am.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_nonmotorpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_nonmotor_pm.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_nonmotormd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_nonmotor_md.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_nonmotornt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_nonmotor_nt.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}



void convert_nonman_nonmotoram (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_nonmotor_am.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_nonmotorpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_nonmotor_pm.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_nonmotormd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_nonmotor_md.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_nonmotornt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 1;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_nonmotor_nt.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}

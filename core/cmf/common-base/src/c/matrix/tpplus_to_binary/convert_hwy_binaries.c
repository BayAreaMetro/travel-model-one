/* Convert highway binary matrices to the TP+ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


void convert_man_hwyam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_sov_am.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_hov_am.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_sov_am_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_hov_am_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_hwypm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_sov_pm.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_hov_pm.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_sov_pm_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_hov_pm_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_hwymd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_sov_md.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_hov_md.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_sov_md_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_hov_md_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_hwynt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_sov_nt.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_hov_nt.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_sov_nt_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_hov_nt_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_hwyam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_sov_am.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_hov_am.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_sov_am_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_hov_am_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_hwypm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_sov_pm.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_hov_pm.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_sov_pm_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_hov_pm_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_hwymd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_sov_md.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_hov_md.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_sov_md_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_hov_md_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_hwynt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 4;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);




	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_sov_nt.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_hov_nt.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_sov_nt_veh.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_hov_nt_veh.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}

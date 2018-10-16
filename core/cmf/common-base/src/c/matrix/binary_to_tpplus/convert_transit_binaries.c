/* Convert transit binary matrices to the TP+ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


void convert_man_transitam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_walktran_lbs_am.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_walktran_ebs_am.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_walktran_brt_am.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_walktran_lrt_am.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\man_walktran_crl_am.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\man_drivtran_lbs_am.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\man_drivtran_ebs_am.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\man_drivtran_brt_am.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\man_drivtran_lrt_am.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\man_drivtran_crl_am.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\man_trandriv_lbs_am.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\man_trandriv_ebs_am.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\man_trandriv_brt_am.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\man_trandriv_lrt_am.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\man_trandriv_crl_am.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}



void convert_man_transitpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_walktran_lbs_pm.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_walktran_ebs_pm.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_walktran_brt_pm.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_walktran_lrt_pm.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\man_walktran_crl_pm.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\man_drivtran_lbs_pm.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\man_drivtran_ebs_pm.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\man_drivtran_brt_pm.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\man_drivtran_lrt_pm.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\man_drivtran_crl_pm.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\man_trandriv_lbs_pm.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\man_trandriv_ebs_pm.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\man_trandriv_brt_pm.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\man_trandriv_lrt_pm.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\man_trandriv_crl_pm.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_transitmd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_walktran_lbs_md.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_walktran_ebs_md.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_walktran_brt_md.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_walktran_lrt_md.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\man_walktran_crl_md.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\man_drivtran_lbs_md.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\man_drivtran_ebs_md.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\man_drivtran_brt_md.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\man_drivtran_lrt_md.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\man_drivtran_crl_md.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\man_trandriv_lbs_md.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\man_trandriv_ebs_md.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\man_trandriv_brt_md.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\man_trandriv_lrt_md.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\man_trandriv_crl_md.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_man_transitnt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\man_walktran_lbs_nt.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\man_walktran_ebs_nt.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\man_walktran_brt_nt.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\man_walktran_lrt_nt.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\man_walktran_crl_nt.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\man_drivtran_lbs_nt.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\man_drivtran_ebs_nt.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\man_drivtran_brt_nt.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\man_drivtran_lrt_nt.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\man_drivtran_crl_nt.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\man_trandriv_lbs_nt.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\man_trandriv_ebs_nt.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\man_trandriv_brt_nt.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\man_trandriv_lrt_nt.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\man_trandriv_crl_nt.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}



void convert_nonman_transitam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_walktran_lbs_am.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_walktran_ebs_am.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_walktran_brt_am.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_walktran_lrt_am.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\nonman_walktran_crl_am.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\nonman_drivtran_lbs_am.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\nonman_drivtran_ebs_am.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\nonman_drivtran_brt_am.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\nonman_drivtran_lrt_am.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\nonman_drivtran_crl_am.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\nonman_trandriv_lbs_am.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\nonman_trandriv_ebs_am.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\nonman_trandriv_brt_am.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\nonman_trandriv_lrt_am.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\nonman_trandriv_crl_am.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}



void convert_nonman_transitpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_walktran_lbs_pm.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_walktran_ebs_pm.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_walktran_brt_pm.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_walktran_lrt_pm.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\nonman_walktran_crl_pm.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\nonman_drivtran_lbs_pm.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\nonman_drivtran_ebs_pm.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\nonman_drivtran_brt_pm.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\nonman_drivtran_lrt_pm.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\nonman_drivtran_crl_pm.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\nonman_trandriv_lbs_pm.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\nonman_trandriv_ebs_pm.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\nonman_trandriv_brt_pm.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\nonman_trandriv_lrt_pm.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\nonman_trandriv_crl_pm.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_transitmd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_walktran_lbs_md.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_walktran_ebs_md.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_walktran_brt_md.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_walktran_lrt_md.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\nonman_walktran_crl_md.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\nonman_drivtran_lbs_md.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\nonman_drivtran_ebs_md.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\nonman_drivtran_brt_md.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\nonman_drivtran_lrt_md.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\nonman_drivtran_crl_md.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\nonman_trandriv_lbs_md.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\nonman_trandriv_ebs_md.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\nonman_trandriv_brt_md.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\nonman_trandriv_lrt_md.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\nonman_trandriv_crl_md.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}


void convert_nonman_transitnt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName) {

    void combineBinaryTablesInTpplusFile (char **binaryFileNames, char *tppFileName, int ntables);


	int i;
	int nTables = 15;
	char **binaryFileNames;
	char fileName[1024];

	strcpy (fileName, tppFilesDirectory);
	strcat (fileName, tppFileName);


	binaryFileNames = (char **) calloc (nTables, sizeof(char *));
	for (i=0; i < nTables; i++)
		binaryFileNames[i] = (char *) calloc (1024, sizeof(char));



	strcpy (binaryFileNames[0], binaryFilesDirectory);
	strcat (binaryFileNames[0], "\\nonman_walktran_lbs_nt.binary");

	strcpy (binaryFileNames[1], binaryFilesDirectory);
	strcat (binaryFileNames[1], "\\nonman_walktran_ebs_nt.binary");

	strcpy (binaryFileNames[2], binaryFilesDirectory);
	strcat (binaryFileNames[2], "\\nonman_walktran_brt_nt.binary");

	strcpy (binaryFileNames[3], binaryFilesDirectory);
	strcat (binaryFileNames[3], "\\nonman_walktran_lrt_nt.binary");

	strcpy (binaryFileNames[4], binaryFilesDirectory);
	strcat (binaryFileNames[4], "\\nonman_walktran_crl_nt.binary");

	strcpy (binaryFileNames[5], binaryFilesDirectory);
	strcat (binaryFileNames[5], "\\nonman_drivtran_lbs_nt.binary");

	strcpy (binaryFileNames[6], binaryFilesDirectory);
	strcat (binaryFileNames[6], "\\nonman_drivtran_ebs_nt.binary");

	strcpy (binaryFileNames[7], binaryFilesDirectory);
	strcat (binaryFileNames[7], "\\nonman_drivtran_brt_nt.binary");

	strcpy (binaryFileNames[8], binaryFilesDirectory);
	strcat (binaryFileNames[8], "\\nonman_drivtran_lrt_nt.binary");

	strcpy (binaryFileNames[9], binaryFilesDirectory);
	strcat (binaryFileNames[9], "\\nonman_drivtran_crl_nt.binary");

	strcpy (binaryFileNames[10], binaryFilesDirectory);
	strcat (binaryFileNames[10], "\\nonman_trandriv_lbs_nt.binary");

	strcpy (binaryFileNames[11], binaryFilesDirectory);
	strcat (binaryFileNames[11], "\\nonman_trandriv_ebs_nt.binary");

	strcpy (binaryFileNames[12], binaryFilesDirectory);
	strcat (binaryFileNames[12], "\\nonman_trandriv_brt_nt.binary");

	strcpy (binaryFileNames[13], binaryFilesDirectory);
	strcat (binaryFileNames[13], "\\nonman_trandriv_lrt_nt.binary");

	strcpy (binaryFileNames[14], binaryFilesDirectory);
	strcat (binaryFileNames[14], "\\nonman_trandriv_crl_nt.binary");


	combineBinaryTablesInTpplusFile (binaryFileNames, fileName, nTables);


	for (i=0; i < nTables; i++)
		free (binaryFileNames[i]);
	free (binaryFileNames);

}

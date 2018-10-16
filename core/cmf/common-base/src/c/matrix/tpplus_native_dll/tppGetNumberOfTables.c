/*=========================================================================*/
/*  Read a matrix randomly */


#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

// declaring global function pointers
extern pFunc_FileInquire       pf_FileInquire;
extern pFunc_TppMatOpenIP      pf_TppMatOpenIP;
extern pFunc_TppMatClose       pf_TppMatClose;

/**
 * Get the number of tables from a TP+ matrix on disk.    
 * 
 * @param fileName - Path to the file to read.
 */
int tppGetNumberOfTables (char *inputFilename) {


	int     i;
    char    *pLicenseFile=NULL;
	int     numTables;


	i = pf_FileInquire(inputFilename, &Ilist);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <=0) {
		printf("\nError in native C code.\n");
		printf("An error occurred in tppGetNumberOfTables() for file=%s, pf_TppMatOpenIP() returned %d.\n\n", inputFilename, i);
		fflush (stdout);
		return (-1);
	}

	numTables = Ilist->mats;
	
	pf_TppMatClose(Ilist);

	return (numTables);
}

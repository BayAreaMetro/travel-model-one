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
 * Get the number of rows from a TP+ matrix on disk.    
 * 
 * @param fileName - Path to the file to read.
 */
int tppGetNumberOfRows (char *inputFilename) {


	int     i;
    char    *pLicenseFile=NULL;
	int     numZones;

	i = pf_FileInquire(inputFilename, &Ilist);

	//printf ("inputFilename=%s, i=%d\n", inputFilename, i);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <=0) {
		printf("\nError in native C code.\n");
		printf("An error occurred in tppGetNumberOfRows() for file=%s, pf_TppMatOpenIP() returned %d.\n", inputFilename, i);
		fflush (stdout);
		return (-1);
	}

	numZones = Ilist->zones;

	pf_TppMatClose(Ilist);

	return (numZones);
}

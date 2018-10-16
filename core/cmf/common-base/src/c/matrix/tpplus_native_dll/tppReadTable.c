/*=========================================================================*/
/*  Read an entire matrix file sequentially */

#include "testio.h"


extern MATLIST *list;
extern MATLIST *Ilist;

// declaring global function pointers
extern pFunc_FileInquire       pf_FileInquire;
extern pFunc_TppMatOpenIP      pf_TppMatOpenIP;
extern pFunc_TppMatClose       pf_TppMatClose;
extern pFunc_TppMatReadSelect  pf_TppMatReadSelect;

/**
 * Read a TP+ matrix file from disk, only for a single table.  
 * 
 * @param fileName - Path to the file to read.
 * @param MatrixIP - A single array of data in which to store the results,
 *                   rows, then cols: double[nRows*nCols].
 * @param table    - The index of the table to read (1-based).  
 */
void tppReadTable (char *inputFilename, double *MatrixIP, int table) {


	int     i, j;
    char    *pLicenseFile=NULL;
    double  *MatWrk;

	i=pf_FileInquire(inputFilename, &Ilist);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <= 0) {
		printf("\nError in native C code.\n");
		printf("An error occurred in tppReadTable() for file=%s, pf_TppMatOpenIP() returned %d.\n\n", inputFilename, i);
		fflush (stdout);
		exit (1);
	}
	
	if (table>Ilist->mats || table<=0) {
		printf("\nError in native C code.\n");
		printf("An error occured in tppReadTable(): table number %i not valid for file=%s with %i tables.\n", table, inputFilename, Ilist->mats); 
		fflush(stdout); 
		exit(1); 
	}

	Ilist->buffer = malloc(Ilist->bufReq);

	for (i=1; i<=Ilist->zones; i++) {      /* I loop */
		//printf("reading row %i\n",i);
        MatWrk = MatrixIP + (i-1)*Ilist->zones;

		if ((j = pf_TppMatReadSelect (Ilist, i, table, MatWrk)) ==0){
			printf("\nRead error at row %i %i:return=%i", i, table, j);
			fflush (stdout);
			exit(1);
		}
	}

	/* must free user allocated buffer before closing */
	free(Ilist->buffer);

	pf_TppMatClose(Ilist);
}

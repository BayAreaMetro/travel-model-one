/*=========================================================================*/
/* Write a TP+ Output Matrix row */


#include "testio.h"

// declaring global function pointers
extern pFunc_TppMatOpenOP      pf_TppMatOpenOP;
extern pFunc_TppMatMatSet      pf_TppMatMatSet;
extern pFunc_TppMatMatResize   pf_TppMatMatResize;
extern pFunc_TppMatMatWriteRow pf_TppMatMatWriteRow;
extern pFunc_TppMatClose		pf_TppMatClose;


int tppWrite (char *fileName, double *MatrixOP, int nzones, int ntables) {


	int     i;
	int     j;
	int     m;
	int		returnValue;
	int     nZones1 = nzones;
	int     nMat1   = ntables;
    char    *b;
    char    *pLicenseFile=NULL;
	char    *psFileName1 = fileName;
    double  *MatWrk;
    time_t	time_beg;


	returnValue = pf_TppMatMatSet(&list, TPP, psFileName1, nZones1, nMat1);

    /* - Allocate a buffer for the file records
       - Set the precision for storing at 2 decimal places
         optional Mspecs is 'D' and 'S' for full precision if necessary
       - Establish a name for each matrix - not absolutely necessary
    */
    list->buffer = malloc(list->bufReq);

    for (i=0; i<nMat1;i++) list->Mspecs[i] = 2;

    for (b=list->Mnames,i=1; i<=nMat1;i++) b += 1 + sprintf(b,"M%i",i);
  


    /* Open the Op file */
	time_beg = time(NULL);

    if ((i = pf_TppMatOpenOP (list, "File ID", "tppOpen()", &time_beg, pLicenseFile, 2)) <= 0) {
        return i;
    }
    pf_TppMatMatResize(&list);




    /*  Write matrix rows */
    for (i=1;i<=list->zones; i++) {     /* Origin Zone loop */
        for (m=1;m<=list->mats;m++) {    /* Matrix Loop      */

			MatWrk = MatrixOP + (i-1)*list->zones*list->mats + (m-1)*list->zones;

			if ((j = pf_TppMatMatWriteRow(list, i, m, list->Mspecs[m-1], MatWrk)) !=1 ) {
				printf("\nWrite error at %i %i:return=%i", i, m, j);
				fflush (stdout);
				exit(1);
			}

        }
    }



    free(list->buffer); /* must free user allocated buffer before closing */
    pf_TppMatClose(list);


	return (0);

}



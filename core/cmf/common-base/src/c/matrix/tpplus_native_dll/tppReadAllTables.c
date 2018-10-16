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
 * This method works, but has been replaced by tppReadTable
 * to save memory, and maintain only one copy.  
 * 
 */
void tppReadAllTables (char *inputFilename, double *MatrixIP) {


	int     i, j, m;
    char    *pLicenseFile=NULL;
    double  *MatWrk;


	i=pf_FileInquire(inputFilename, &Ilist);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <= 0) {
		printf("\nOpenIP Err=%i",i);
		exit(1);
	}

	Ilist->buffer = malloc(Ilist->bufReq);



	for (i=1; i<=Ilist->zones; i++) {      /* I loop */
		for (m=1; m<=Ilist->mats; m++) {     /* m loop */

            MatWrk = MatrixIP + (i-1)*Ilist->zones*Ilist->mats + (m-1)*Ilist->zones;

			if ((j = pf_TppMatReadSelect (Ilist, i, m, MatWrk)) !=1 ){
				printf("\nRead error at %i %i:return=%i", i, m, j);
				exit(1);
			}


		}
	}


	/* must free user allocated buffer before closing */
	free(Ilist->buffer);

	pf_TppMatClose(Ilist);

}

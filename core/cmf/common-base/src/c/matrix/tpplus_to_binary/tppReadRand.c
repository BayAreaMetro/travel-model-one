/*=========================================================================*/
/*  Read a matrix randomly */


#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

// declaring global function pointers
extern pFunc_FileInquire       pf_FileInquire;
extern pFunc_TppMatOpenIP      pf_TppMatOpenIP;
extern pFunc_TppMatClose       pf_TppMatClose;
extern pFunc_TppMatReadNext    pf_TppMatReadNext;
extern pFunc_TppMatReadDirect  pf_TppMatReadDirect;


int tppReadRand (char *inputFilename, int table, int row, double *rowData) {


	int     i;
	int     j;
    int     pRowPtrs;
    char    *pLicenseFile=NULL;
	char    *psFileName1 = inputFilename;



	i=pf_FileInquire(psFileName1, &Ilist);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <=0) {
		printf("\nOpenIP Err=%i",i);
		return abs(i);
	}


	Ilist->buffer = malloc(Ilist->bufReq);


    /* scan file to save pointers to each row wanted randomly */
	i = 1;
    while (pf_TppMatReadNext(1,Ilist,rowData) == 1) {

        if (Ilist->rowOrg > Ilist->zones) break;     /* shouldn't be */
        if (Ilist->rowMat == table && Ilist->rowOrg == row) {
			pRowPtrs = Ilist->rowpos;
			break;
		}
        pf_TppMatReadNext(-2,Ilist,rowData);
	}	


    if ((j=pf_TppMatReadDirect (Ilist, pRowPtrs, rowData)) !=1 ) {
        printf("\nRead error at %i: return=%i", i, j);
        return abs(j);
    }

	/* must free user allocated buffer before closing */
	free(Ilist->buffer);

	pf_TppMatClose(Ilist);

	return (0);
}
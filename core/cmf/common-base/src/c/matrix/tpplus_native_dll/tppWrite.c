/*=========================================================================*/
/* Write a TP+ Output Matrix row */


#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

// declaring global function pointers
extern pFunc_TppMatOpenOP      pf_TppMatOpenOP;
extern pFunc_TppMatMatSet      pf_TppMatMatSet;
extern pFunc_TppMatMatResize   pf_TppMatMatResize;
extern pFunc_TppMatMatWriteRow pf_TppMatMatWriteRow;
extern pFunc_TppMatClose       pf_TppMatClose;

/**
 * Writes a TP+ matrix file to disk, all tables.  
 * 
 * @param fileName   - Path to the file to write.
 * @param MatrixOP   - A single array of data to write, rows, then tables, 
 * 					   then columns: float[nRows*nTables*nCols].
 * @param tableNames - A single string of table names, delimited by spaces.
 * @param nzones     - Number of zones (supports square matrices only). 
 * @param ntables    - Number of tables. 
 * @param precision  - Decimals of precision used to store output
 *                        (full precision 'D' and 'S' not supported. 
 * 
 */ 
int tppWrite (char *fileName, float *MatrixOP, char *tableNames, 
              int nzones, int ntables, int precision) {


	int     i;
	int     j;
	int     m;
	int     c; 
	int     y; 
	int		returnValue;
	int     nZones1 = nzones;
	int     nMat1   = ntables;
	int     precision1 = precision; 
    char    *b;
    char    *pLicenseFile=NULL;
	char    *psFileName1 = fileName;
    double  *rowptr; 
    time_t	time_beg;
    
        
    rowptr = (double *) malloc( ((nZones1+3)*sizeof(double)) );

	returnValue = pf_TppMatMatSet(&list, TPP, psFileName1, nZones1, nMat1);

    list->buffer = malloc(list->bufReq);
    
    if (precision1<0 || precision1>9) {
        printf("\nError in native C code.\n");
		printf("An error occurred in tppWrite(): Invalid precision %i, must be 0-9.\n\n", precision1);
		fflush (stdout);
		exit (1);
    }
    for (i=0; i<nMat1;i++) {
    	 list->Mspecs[i] = precision1;
    }

	// convert from a single string separated by spaces, to an array of strings
	y=0; 	
    for (b=list->Mnames,i=1; i<=nMat1;i++) {
		int x=0; 
		char nameBuf[MAX_STRING];     	
		while (x<MAX_STRING && tableNames[y]!=' ') {
			nameBuf[x] = tableNames[y]; 
			x++;
			y++; 
		}
		y++; 
		nameBuf[x] = '\0'; 
		b += 1 + sprintf(b,"%s",nameBuf);
	}
    

    /* Open the Op file */
	time_beg = time(NULL);

    if ((i = pf_TppMatOpenOP (list, "File ID", "tppOpen()", &time_beg, pLicenseFile, 2)) <= 0) {
        printf("\nError in native C code.\n");
		printf("An error occurred in tppWrite() for file=%s, pf_TppMatOpenOP() returned %d.\n\n", fileName, i);
		fflush (stdout);
		exit (1);
    }
    pf_TppMatMatResize(&list);



    /*  Write matrix rows */
    for (i=1;i<=list->zones; i++) {     /* Origin Zone loop */
        for (m=1;m<=list->mats;m++) {    /* Matrix Loop      */

			int startPosition = (i-1)*list->zones*list->mats + (m-1)*list->zones;
			
			for(c=0;c<=list->zones;c++) {
               	rowptr[c]=(double)(MatrixOP[startPosition+c]);      
            } 

			if ((j = pf_TppMatMatWriteRow(list, i, m, list->Mspecs[m-1], rowptr)) !=1 ) {
				printf("\nWrite error at %i %i:return=%i", i, m, j);
				fflush (stdout);
				exit(1);
			}

        }
    }
	
	/* must free user allocated buffer before closing */
	free(rowptr); 
	free(list->buffer);
	pf_TppMatClose(list);
	
	return (0);

}



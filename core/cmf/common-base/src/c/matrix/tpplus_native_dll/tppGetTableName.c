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
 * @param table    - The index of the table to read (1-based).  
 */
char* tppGetTableName (char *inputFilename, int table) {


	int     i;
    char    *pLicenseFile=NULL;
    char*   tableName = "";
    char    tempbuf[255];
	char*   c;

	i = pf_FileInquire(inputFilename, &Ilist);

	if ((i = pf_TppMatOpenIP(Ilist, pLicenseFile, 2)) <=0) {
		printf("\nError in native C code.\n");
		printf("An error occurred in tppGetTableName() for file=%s, pf_TppMatOpenIP() returned %d.\n\n", inputFilename, i);
		fflush (stdout);
		exit (1);
	}
	
	if (table>Ilist->mats || table<=0) {
		printf("\nError in native C code.\n");
		printf("An error occured in tppGetTableName(): table number %i not valid for file=%s with %i tables.\n", table, inputFilename, Ilist->mats); 
		fflush(stdout); 
		exit(1); 
	}

	
	
    //Store table names
    c = (char *) Ilist->Mnames;
    
    for (i=1; i <= Ilist->mats; i++) {

        sprintf (tempbuf, "%s", c);
        
		if(i==table) {
			tableName = (char *) malloc( (strlen(tempbuf)+1) *sizeof(char));
			strcpy (tableName, tempbuf);
			break;
		}

        c = c + strlen(c) + 1;
    }

	pf_TppMatClose(Ilist);

	return tableName; 	
}


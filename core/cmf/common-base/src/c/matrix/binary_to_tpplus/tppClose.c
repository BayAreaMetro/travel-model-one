/*=========================================================================*/
/* Close the TP+ I/O data */


#include "testio.h"


extern pFunc_TppMatClose pf_TppMatClose;


int tppClose () {

    free(list->buffer); /* must free user allocated buffer before closing */
    pf_TppMatClose(list);

	return (0);
}
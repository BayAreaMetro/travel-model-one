#include <jni.h>
#include <windows.h>
#include "TppMatio.h"
#include "testio.h"

MATLIST *list;
MATLIST *Ilist;

// declaring global function pointers
pFunc_FileInquire       pf_FileInquire;
pFunc_TppMatOpenIP      pf_TppMatOpenIP;
pFunc_TppMatOpenOP      pf_TppMatOpenOP;
pFunc_TppMatClose       pf_TppMatClose;
pFunc_TppMatMatSet      pf_TppMatMatSet;
pFunc_TppMatMatResize   pf_TppMatMatResize;
pFunc_TppMatReadNext    pf_TppMatReadNext;
pFunc_TppMatReadDirect  pf_TppMatReadDirect;
pFunc_TppMatReadSelect  pf_TppMatReadSelect;
pFunc_TppMatMatWriteRow pf_TppMatMatWriteRow;
pFunc_TppMatPos         pf_TppMatPos;

/**
 * Java interface to initialize TP+ I/O procedures.   
 * @see com.pb.common.matrix.TpplusNativeIO.java
 * 
 * @call tppInitDllNative ();
 * 
 * Need to ensure that tppdlibx.dll (included with Cube) is available
 * in the system's path.  
 * 
 */
JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppInitDllNative (JNIEnv *jEnv, jobject jobj)
{

	LPVOID lpMsgBuf;
	DWORD dw;

	// Link DLL
	HMODULE hMod = LoadLibrary("tppdlibx.dll");
	if (hMod == NULL) {
		printf("Could not load tppdlibx.dll\n");
		    
		 // Retrieve the system error message for the last-error code
    	dw = GetLastError(); 
    	FormatMessage(
	        FORMAT_MESSAGE_ALLOCATE_BUFFER | 
    	    FORMAT_MESSAGE_FROM_SYSTEM |
        	FORMAT_MESSAGE_IGNORE_INSERTS,
        	NULL,
        	dw,
        	MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        	(LPTSTR) &lpMsgBuf,
        	0, NULL );
    	printf(TEXT("Failed with error %d: %s"), dw, lpMsgBuf); 
	    LocalFree(lpMsgBuf);
	}

	// assign function pointers

	if(GetProcAddress(hMod,"_FileInquire")!=NULL){ //pre-cube 4
		pf_FileInquire       = (pFunc_FileInquire) GetProcAddress(hMod,"_FileInquire");
		pf_TppMatOpenIP      = (pFunc_TppMatOpenIP) GetProcAddress(hMod,"_TppMatOpenIP");
		pf_TppMatOpenOP      = (pFunc_TppMatOpenOP) GetProcAddress(hMod,"_TppMatOpenOP");
		pf_TppMatClose       = (pFunc_TppMatClose) GetProcAddress(hMod,"_TppMatClose");
		pf_TppMatMatSet      = (pFunc_TppMatMatSet) GetProcAddress(hMod,"_TppMatSet");
		pf_TppMatMatResize   = (pFunc_TppMatMatResize) (void*)GetProcAddress(hMod,"_TppMatResize");
		pf_TppMatReadNext    = (pFunc_TppMatReadNext) GetProcAddress(hMod,"_TppMatReadNext");
		pf_TppMatReadDirect  = (pFunc_TppMatReadDirect) GetProcAddress(hMod,"_TppMatReadDirect");
		pf_TppMatReadSelect  = (pFunc_TppMatReadSelect) GetProcAddress(hMod,"_TppMatReadSelect");
		pf_TppMatMatWriteRow = (pFunc_TppMatMatWriteRow) GetProcAddress(hMod,"_TppMatWriteRow");
		pf_TppMatPos         = (pFunc_TppMatPos) GetProcAddress(hMod,"_TppMatPos"); 
	}else{ //cube 4 or later
		pf_FileInquire       = (pFunc_FileInquire) GetProcAddress(hMod,"FileInquire");
		pf_TppMatOpenIP      = (pFunc_TppMatOpenIP) GetProcAddress(hMod,"TppMatOpenIP");
		pf_TppMatOpenOP      = (pFunc_TppMatOpenOP) GetProcAddress(hMod,"TppMatOpenOP");
		pf_TppMatClose       = (pFunc_TppMatClose) GetProcAddress(hMod,"TppMatClose");
		pf_TppMatMatSet      = (pFunc_TppMatMatSet) GetProcAddress(hMod,"TppMatSet");
		pf_TppMatMatResize   = (pFunc_TppMatMatResize) (void*)GetProcAddress(hMod,"TppMatResize");
		pf_TppMatReadNext    = (pFunc_TppMatReadNext) GetProcAddress(hMod,"TppMatReadNext");
		pf_TppMatReadDirect  = (pFunc_TppMatReadDirect) GetProcAddress(hMod,"TppMatReadDirect");
		pf_TppMatReadSelect  = (pFunc_TppMatReadSelect) GetProcAddress(hMod,"TppMatReadSelect");
		pf_TppMatMatWriteRow = (pFunc_TppMatMatWriteRow) GetProcAddress(hMod,"TppMatWriteRow");
		pf_TppMatPos         = (pFunc_TppMatPos) GetProcAddress(hMod,"TppMatPos"); 
    }
}

#include "testio.h"


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


void tppInitDllNative ()
{

	// Link DLL
	HMODULE hMod = LoadLibrary("tppdlibx.dll");

	// assign function pointers
	if(GetProcAddress(hMod,"_FileInquire")!=NULL){  //pre-Cube 4.0

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
	}else{ //Cube 4 or later
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
}

}

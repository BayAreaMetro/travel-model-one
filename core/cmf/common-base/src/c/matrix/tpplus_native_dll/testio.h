/*  This example illustrates reading and writing of Citilabs' native
    matrix files. Using other entry points as described herein allows
    the user to do special proessing.

OP:     is the block that illustrates writing a matrix file
IP:     is the block that illustrates reading a matrix file sequentially
RAND:   is the block that illustrates reading a matrix file randomly


    02/04/03 In order for any executable to use these routines, the exe
    must be in the same directory where Citilabs software is installed.
    If the exe requires system, or support routines to be loaded, it is
    the exe's responsibility to determine how that linkage is to be
    accomplished.  The easiest way is for the exe and its support
    routines to be in the Citilabs directory.  If this causes a problem
    the user will have to call Citilabs tech support to get additional
    information.



    NOTES about MATLIST:
    MATLIST is actually longer than the definition,
            but can be resized by TppMatResize -- not necessary.
    FileName is placed after buffer.
    Mspecs   is placed after Filename
    Mnames   is placed after Mspecs

    buffer MUST be allocated and filled in by the Caller; it may be shared
    by other caller areas.  It is used only as a temporary buffer during an
    entry.  It must be at least bufReq bytes long.

    For I/P,  list is usually allocated by FileInq which determines what
    type of file it is.

    For O/P, the user may allocate list, but TppMatSet is recommended to
    allocate and initialize list.

    Caller is responsible to allocate and provide the required buffers
    as determined by the routines.  Buffers can be shared across files, so
    user can allocate one buffer and place its pointer in all open lists.


    Entry to functions are listed below:
        Almost all calls return 1 for success and 0, or negative, for failure

        list is a ptr to an MATLIST, and is key in almnost all calls
        User must fill in parts of list before Open
        INT = typedef for int


    INT   TppMatOpenIP (MATLIST *list, char *pPgmPath, INT FileType) -- Open a file
            list was allocated by FileInq, but can be allocated by caller
            pPgmPath  = NULL for normal use
                        Call Citilabs if problems, or for special applications
            FileType  = 1 if license is Viper, 2 if TP+
            Return: 0 = err -- shouldn't happen
                    1   OK
                  - 1   not recognized,
                  -11   License file not found
                  -12   Invalid License file
                  -13   Registry Entry not found
                  -14   License expired (tppdlibx.dll)
                  -15   Dongle driver Missing
                  -16   Dongle not found
                  -17   Dongle Test failed Authentication
                  -18   License Mismatch Lookingfor=maxzones, fnd=maxnodes
                  -19   Too many processors - license isn't valid
                  -20   Maximum zone numbers allowed

    INT   TppMatOpenOP (MATLIST *list, char *ID, char *pgm, void* time_beg,
                        char *pPgmPath, INT FileType);
            list     = MATLIST allocated (most likely by TpMatSet)
            ID       = up to 60 character ID for file
            pgm      = character name for your program - placed in file
            time_beg = current date/time from c library routine time();
            pPgmPath = NULL for normal use
                       Call Citilabs if problems, or for special applications
            FileType = 1 if license is Viper, 2 if TP+

            Return:  0=err, 1=OK, -x = LicenseErr -- see OpenIP

            User must fill in these list->elements BEFORE calling this OPen:
                type;     1=TP+, 2=MINUTP, 3=TRANPLAN, 5=TRIPS
                zones;
                mats;
                buffer;   TPP,MU,TRNPLN = (Z*2+10)*8, (Z*2+2)*4, Z*4+1010
                FileName[...];
                MatSpecs[mats];
                MatNames[mats*strlens];
            This is probably best handled by using TppMatSet to allocate list
            and populate the required elements.

    INT   TppMatSet(MATLIST **list,int type,char *FileName,int zones,int mats)
            list  = the MATLIST structure
            type  = type of matrix file, see OpenOP
            name  = name of the matrix file
            zones = number of zones
            mats  = number of matrices to be written

            Return: 0=err, 1=OK

            Between TppMatSet and TppMatOpenOP:
             - allocate a work buffer: list->buffer = malloc(list->bufReq);
             - optionally set precision for each matrix (default = 0)
                for (i=0; i<mats;i++) list->Mspecs[i] = #;
                    # = 0-9 for number of decimal precision to carry
                    'S' = store as single precision
                    'D' = store as double precision
                    S and D provide very little precision
             - optionally set a name for each matrix
                for (b=list->Mnames,i=1; i<=mats;i++)
                    b += 1 + sprintf(b,"M%i",i);
                 or b += 1 + strlen(strcpy(b,Matname[i]));

                or char names[]={"name1\0" "name2\0" "name3\0...."}
                   memcpy(list->Mnames,names,sizeof(names))


    MATLIST *TppMatResize(MATLIST **list)
            optionally can be called after TppMatOpenOp to resize list
            (and possibly move it -- by system routine)
            TppMatSet had to open with more than actual required space,
             the extra space can be released by this routine;
             it is not necessary -- just good housekeeping


    INT   TppMatPos(MATLIST *list,DWORD loc) -- Position to begin matrix record
            loc = 0 = to first row
                 >0 = to that location
            Return:  0=err, 1=OK

    INT   TppMatReadNext (INT op, MATLIST *list, void *matrix) -- read next row
            op = 1 Read Header
                 2 Read data
                -2 Skip data
                 3 Read header and data
            matrix = double row to be filled in (routine will clear it first)
            Return: 0=err, 1=OK

    INT   TppMatReadSelect (MATLIST *list, INT org,INT tab,void *matrix) -- read to a selected row
            org      = origin zone wanted (may not be behind current position)
            tab      = matrix number wanted
            matrix   = row to be filled in (routine will clear it first)
            Return: 0=err, 1=OK, -1=not found

    INT   TppMatReadDirect (MATLIST *list,DWORD location,void *matrix) -- read a row at location
            location = file position
            matrix = row to be filled in (routine will clear it first)
            Return: 0=err, 1=OK

    INT   TppMatClose  (MATLIST *list);
            Return: 0=err, 1=OK

    INT   TppMatWrite(MATLIST *list, void *buffer, INT lng) {
            buffer = buffer to write to file (not a matrix row)
            lng    = length of buffer
            return results of direct write  (1=OK)

    INT   TppMatRead(lMATLIST *list, void *buffer, INT lng) {
            buffer = where to read data into (no conversion, etc.)
            lng    = amount to read
            return results of direct read (1=OK)

    INT   TppMatGetPos(MATLIST *list) {
            return file position

    INT   TppMatSeek(MATLIST *list, LONG offset, INT whence) {
            c library fseek(...) is used
            offset = position to seek to
            whence indicates offset is from:
                0=beginning_of_file, 1=current_position, 2=EOF
            return results of positioning (1=OK)

Typical file formats handled directly: TP+  MINUTP  TRANPLAN  TRIPS
The user need not know the format for IP -- it is transparent.
The user has to set the format for O/P

*/


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <windows.h>

typedef struct {
        WORD    length;    // can be resized to this length
        BYTE    type;      // type of file (1-2-3 = TPP, MINUTP, TRANPLAN)
        BYTE    dummy;     //
        FILE*   ptr;       // pointer
        BYTE    start;     // required for use with TRANPLAN I/P
        BYTE    remain;    // required for use with TRANPLAN I/P
        BYTE    rowStart;  // required for use with TRANPLAN I/P
        BYTE    rowRemain; // required for use with TRANPLAN I/P
        WORD    zones;     // number of zones
        WORD    mats;      // number of matrices per zone
        WORD    Zones;     // system zones
        DWORD   row0pos;   // location to position to row 1 for TPP
        DWORD   rowpos;    // position where this row was located on file
        WORD    rowWords;  // header of current row
        WORD    rowOrg;    // header of current row
        WORD    rowMat;    // header of current row
        double  rowsum;    // for Output
        DWORD   bufReq;    //
        char*   FileName;  // pointer to filename
        BYTE*   Mspecs;    // pointer to varBytes;
        BYTE*   Mnames;    // pointer to varNames;
        void*   buffer;    // location of required buffer (i/o & work)
        } MATLIST ;

typedef int ( *pFunc_FileInquire)  (char*, MATLIST**);
typedef int ( *pFunc_TppMatOpenIP) (MATLIST*, char*, int);
typedef int ( *pFunc_TppMatReadSelect)(MATLIST*, int, int, void*);
typedef int ( *pFunc_TppMatClose)  (MATLIST*);
typedef int ( *pFunc_TppMatOpenOP) (MATLIST*, char*, char*, void*,char*, int);
typedef int ( *pFunc_TppMatReadNext) (int, MATLIST*, void*);
typedef int ( *pFunc_TppMatMatSet) (MATLIST **UMlist,int type,char *name,int zones,int matrices);
typedef MATLIST* ( *pFunc_TppMatMatResize)(MATLIST **UMlist);
typedef int ( *pFunc_TppMatMatWriteRow) (MATLIST *list, int nOrg, int nMat, int  nForm, void *matrix);
typedef int ( *pFunc_TppMatReadDirect) (MATLIST *list,DWORD location,void *matrix);
typedef int ( *pFunc_TppMatPos)    (MATLIST *list,DWORD loc);

#define     TPP      1
#define     MINUTP   2
#define     TRANPLAN 3
#define     TRIPS    5

#define  MAX_TABLES  500
#define  MAX_STRING  255

//static MATLIST *list;
//static MATLIST *Ilist;


/*===========================================================================*/

/* Convert skim matrix tables in TP+ matrix file to binary matrix format suitable for java programs to read */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <io.h>



void main (int argc, char **argv) {

	void splitTpplusTablesIntoBinaryFiles (char *tppFileName, char *tpplusFilesDirectory, char *binaryFilesDirectory);
	void tppInitDllNative ();


	char *binaryFilesDirectory;
	char *tpplusFilesDirectory;
 	int  ch = '.';
	char *extension;
	char filesPath[5000];
	struct _finddata_t file;
    long hFile;


	// the argument list should be tpplus directoy, binary directory
	if (argc != 3) {
		printf ("usage: covertTpplusBinary <tpplus files directory name>, <binary files diretory name>.\n");
		fflush(stdout);
		exit (-2);
	}
	else {
		tpplusFilesDirectory = argv[1];
		binaryFilesDirectory = argv[2];


		printf ("covertTpplusBinary: converting tpplus files in %s to binary files in %s\n", tpplusFilesDirectory, binaryFilesDirectory);
		strcpy(filesPath,tpplusFilesDirectory);
		strcat(filesPath,"\\*.*");
		fflush(stdout);
	}



	tppInitDllNative ();

   if( (hFile = _findfirst( filesPath, &file )) == -1L )
		printf("No files found\n");
	
	while( _findnext( hFile, &file ) == 0 )
	{
			// what we're doing here is isolating the bit
			// that tells us if the handle points to a 
			// directory
			if ((file.attrib & _A_SUBDIR )==0) // if we are a directory, skip
			{
				extension = strrchr(file.name, ch);

				//convert files with .skm or .mtx extension
				if(strcmp(extension, ".skm")==0||strcmp(extension, ".mtx")==0){
					printf(" converting %s\n",file.name);
					splitTpplusTablesIntoBinaryFiles (file.name, tpplusFilesDirectory, binaryFilesDirectory);
				}
			}
	}
	_findclose( hFile );

/*
	splitTpplusTablesIntoBinaryFiles ("hwymd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("bestdram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("bestdrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("bestwkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("bestwkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lbusdram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lbusdrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lbuswkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lbuswkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("ebusdram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("ebusdrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("ebuswkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("ebuswkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("brtdram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("brtdrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("brtwkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("brtwkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lrtdram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lrtdrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lrtwkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("lrtwkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("crldram.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("crldrmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("crlwkam.skm", tpplusFilesDirectory, binaryFilesDirectory);
	splitTpplusTablesIntoBinaryFiles ("crlwkmd.skm", tpplusFilesDirectory, binaryFilesDirectory);
*/
}

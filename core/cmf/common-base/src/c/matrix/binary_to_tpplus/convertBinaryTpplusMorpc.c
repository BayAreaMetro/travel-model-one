/* Convert binary matrices to the TP+ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


void main (int argc, char **argv) {

	void convert_man_hwyam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_hwypm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_hwymd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_hwynt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_hwyam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_hwypm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_hwymd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_hwynt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_transitam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_transitpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_transitmd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_transitnt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_transitam (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_transitpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_transitmd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_transitnt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_nonmotoram (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_nonmotorpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_nonmotormd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_man_nonmotornt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_nonmotoram (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_nonmotorpm (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_nonmotormd (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void convert_nonman_nonmotornt (char *binaryFilesDirectory, char *tppFilesDirectory, char *tppFileName);
	void tppInitDllNative ();


	char *binaryFilesDirectory;
	char *tpplusFilesDirectory;




	// the argument list should be binary directory, tpplus directoy
	if (argc != 3) {
		printf ("usage: covertBinaryTpplus <binary files diretory name>, <tpplus files diretory name>.\n");
		fflush(stdout);
		exit (-2);
	}
	else {
		binaryFilesDirectory = argv[1];
		tpplusFilesDirectory = argv[2];

		printf ("covertBinaryTpplus: converting binary files in %s to tpplus files in %s.\n", binaryFilesDirectory, tpplusFilesDirectory);
		fflush(stdout);
	}



	tppInitDllNative ();



	convert_man_hwyam ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_hwyam.tpp" );
	convert_man_hwypm ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_hwypm.tpp" );
	convert_man_hwymd ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_hwymd.tpp" );
	convert_man_hwynt ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_hwynt.tpp" );
	convert_nonman_hwyam ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_hwyam.tpp" );
	convert_nonman_hwypm ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_hwypm.tpp" );
	convert_nonman_hwymd ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_hwymd.tpp" );
	convert_nonman_hwynt ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_hwynt.tpp" );



	convert_man_transitam ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_transitam.tpp" );
	convert_man_transitpm ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_transitpm.tpp" );
	convert_man_transitmd ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_transitmd.tpp" );
	convert_man_transitnt ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_transitnt.tpp" );
	convert_nonman_transitam ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_transitam.tpp" );
	convert_nonman_transitpm ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_transitpm.tpp" );
	convert_nonman_transitmd ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_transitmd.tpp" );
	convert_nonman_transitnt ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_transitnt.tpp" );



	convert_man_nonmotoram ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_nonmotoram.tpp" );
	convert_man_nonmotorpm ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_nonmotorpm.tpp" );
	convert_man_nonmotormd ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_nonmotormd.tpp" );
	convert_man_nonmotornt ( binaryFilesDirectory, tpplusFilesDirectory, "\\man_nonmotornt.tpp" );
	convert_nonman_nonmotoram ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_nonmotoram.tpp" );
	convert_nonman_nonmotorpm ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_nonmotorpm.tpp" );
	convert_nonman_nonmotormd ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_nonmotormd.tpp" );
	convert_nonman_nonmotornt ( binaryFilesDirectory, tpplusFilesDirectory, "\\nonman_nonmotornt.tpp" );


}

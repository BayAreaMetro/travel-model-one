#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

/**
 * Java interface to get the number of rows from a TP+ matrix on disk.  
 * @see com.pb.common.matrix.TpplusNativeIO.java  
 * 
 * @call tppGetNumberOfRowsNative (String jfileName);
 * 
 * @param fileName - Path to the file to read.
 */
JNIEXPORT int JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppGetNumberOfRowsNative (JNIEnv *jEnv, jobject jobj, jstring jfileName)
{

	int returnCode;


// native function declarations
	int tppGetNumberOfRows (char *inputFilename);


// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);



	// native function calls
	returnCode = tppGetNumberOfRows (fileName);
	if (returnCode <= 0) {
		printf("\nError in native C code.\n");
		printf("An error occurred in tppGetNumberOfRowsNative() for file=%s, tppGetNumberOfRows() returned %d.\n", fileName, returnCode);
		fflush (stdout);
		exit (-1);
	}


	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);

	return (returnCode);
}

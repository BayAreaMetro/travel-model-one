#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;


JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppReadSeqNative (JNIEnv *jEnv, jobject jobj,
										jstring jfileName, jdoubleArray jdata)
{

// native function declarations
	void tppReadSeq (char *inputFilename, double *MatrixIP);


// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);


	// convert the double array passed from java to a double native C array
	jdouble *localData = (*jEnv)->GetDoubleArrayElements(jEnv, jdata, 0);



	// native function call to read entire matrix file (all tables, all rows and columns)
	tppReadSeq (fileName, (double *)localData);


	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);


	// this tells the vm that the native method is finished with the data array argument passed in.
	(*jEnv)->ReleaseDoubleArrayElements(jEnv, jdata, localData, 0);

	// release memory for the local C space data array
	free (localData);

}

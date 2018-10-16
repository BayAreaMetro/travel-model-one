#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;


JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppReadRandNative (JNIEnv *jEnv, jobject jobj,
										jstring jfileName, jint jtable, jint jrow, jdoubleArray jdata)
{

// native function declarations
	int tppReadRand (char *inputFilename, int table, int row, double *rowData);


// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);

// convert the double array passed from java into a native array
	jdouble *localData = (*jEnv)->GetDoubleArrayElements(jEnv, jdata, 0);


	// native function calls
	tppReadRand (fileName, jtable, jrow, (double *)localData);


	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);

	// this tells the vm that the native method is finished with the data array argument passed in.
	(*jEnv)->ReleaseDoubleArrayElements(jEnv, jdata, localData, 0);

}

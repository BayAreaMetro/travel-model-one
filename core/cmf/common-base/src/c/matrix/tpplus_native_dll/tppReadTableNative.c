#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

/**
 * Java interface to read a TP+ matrix file from disk, only for a single table.  
 * @see com.pb.common.matrix.TpplusNativeIO.java
 * @see com.pb.common.matrix.TpplusMatrixReader.java
 * 
 * @call tppReadTableNative (String jfileName, double[] jdata, int jtable);
 * 
 * @param jfileName - Path to the file to read.
 * @param jdata     - A single array of data in which to store the results,
 *                    rows, then cols: double[nRows*nCols].
 * @param jtable    - The index of the table to read (1-based).  
 */
JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppReadTableNative (JNIEnv *jEnv, jobject jobj,
										jstring jfileName, jdoubleArray jdata, jint jtable)
{

// native function declarations
	void tppReadTable (char *inputFilename, double *MatrixIP, int table);


// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);


	// convert the double array passed from java to a double native C array
	jdouble *localData = (*jEnv)->GetDoubleArrayElements(jEnv, jdata, 0);


	// native function call to read entire matrix file (all tables, all rows and columns)
	tppReadTable (fileName, (double *)localData, jtable);


	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);


	// this tells the vm that the native method is finished with the data array argument passed in.
	(*jEnv)->ReleaseDoubleArrayElements(jEnv, jdata, localData, 0);

	// Jim Hicks - 26mar2008 - Don't need the free().  Memory was freed by (*jEnv)->ReleaseDoubleArrayElements when passed the last parameter=0.
	// release memory for the local C space data array
	// free (localData);

}

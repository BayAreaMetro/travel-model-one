#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

/**
 * Java interface to write a TP+ matrix file to disk, all tables.  
 * @see com.pb.common.matrix.TpplusNativeIO.java
 * @see com.pb.common.matrix.TpplusMatrixWriter.java
 * 
 * @call tppWriteNative (String jfileName, float[] jdata, String jtableNames, int jnrows, int jntables, int jprecision);
 * 
 * @param jfileName  - Path to the file to write.
 * @param jdata      - A single array of data to write, rows, then tables, 
 * 					   then columns: float[nRows*nTables*nCols].
 * @param jtableNames- A single string of table names, delimited by spaces.
 * @param jnrows     - Number of zones (supports square matrices only). 
 * @param jntables   - Number of tables. 
 * @param jprecision - Decimals of precision used to store output
 *                        (full precision 'D' and 'S' not supported. 
 * 
 */ 
JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppWriteNative (JNIEnv *jEnv, jobject jobj,
								jstring jfileName, jfloatArray jdata, jstring jtableNames, 
								jint jnrows, jint jntables, jint jprecision)
{

	// native function declarations
	int tppWrite (char *fileName, float *MatrixOP, char *tableNames, int nzones, int ntables, int precision);



	// convert the double array passed from java into a native array
	jfloat *localData = (*jEnv)->GetFloatArrayElements(jEnv, jdata, 0);

	// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);
	char *tableNames = (char *)(*jEnv)->GetStringUTFChars(jEnv, jtableNames, 0); 


	// native function calls
	tppWrite (fileName, (float *)localData, tableNames, jnrows, jntables, jprecision);




	// this tells the vm that the native method is finished with the data array argument passed in.
	(*jEnv)->ReleaseFloatArrayElements(jEnv, jdata, localData, 0);

	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);
    (*jEnv)->ReleaseStringUTFChars(jEnv, jtableNames, tableNames);
    

}

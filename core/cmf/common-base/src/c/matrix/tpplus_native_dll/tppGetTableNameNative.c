#include <jni.h>
#include "TppMatio.h"
#include "testio.h"

extern MATLIST *list;
extern MATLIST *Ilist;

/**
 * Java interface to get the number of tables from a TP+ matrix on disk.     
 * @see com.pb.common.matrix.TpplusNativeIO.java   
 * 
 * @call tppGetTableNameNative (String jfileName, int jtable); 
 * 
 * @param fileName - Path to the file to read.
 * @param table    - The index of the table to read (1-based).  
 */
JNIEXPORT jstring JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppGetTableNameNative (JNIEnv *jEnv, jobject jobj, 
																jstring jfileName, jint jtable)
{

	char * returnName; 

// native function declarations
	char* tppGetTableName (char *inputFilename, int table);


// convert the arguments passed from the java method call to native variables
    char *fileName = (char *)(*jEnv)->GetStringUTFChars(jEnv, jfileName, 0);



	// native function calls
	returnName = tppGetTableName (fileName, jtable);


	// this tells the vm that the native method is finished with the string argument passed in.
    (*jEnv)->ReleaseStringUTFChars(jEnv, jfileName, fileName);

	// convert the return value from a native string to a java string
	return (*jEnv)->NewStringUTF(jEnv, returnName); 
}

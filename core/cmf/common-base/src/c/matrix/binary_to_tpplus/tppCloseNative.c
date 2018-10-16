#include <jni.h>
#include "TppMatio.h"
#include "testio.h"


extern MATLIST *list;
extern MATLIST *Ilist;

JNIEXPORT void JNICALL Java_com_pb_common_matrix_TpplusNativeIO_tppCloseNative (JNIEnv *jEnv, jobject jobj)
{

// native function declarations
	int tppClose ();

	// native function calls
	tppClose ();

}

#include <math.h>
#include "mathNative.h"

JNIEXPORT jdouble JNICALL Java_com_pb_common_math_MathNative_log (JNIEnv *jEnv, jobject jobj, jdouble jdoubleArg)
{

	// return the double value returned by the native intrinsic function call
	return ( log(jdoubleArg) );

}

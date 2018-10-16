#
# eg. startMonitor  ~/daf/config/commandfile  ~/daf/machine/startnode.properties
# 
LOGFILE=$BASEDIR/common-base/config/info_logging.properties
CLASSPATH=$BASEDIR/common-base/build/classes:$BASEDIR/common-daf-v2/build/classes:$DAFDIR:
echo $DAFDIR
echo $LOGFILE
echo $CLASSPATH
java -classpath $CLASSPATH -Xmx1200m -Djava.util.logging.config.file=$LOGFILE com.pb.common.daf.admin.FileMonitor $1 $2
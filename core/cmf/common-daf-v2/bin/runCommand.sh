LOGFILE=$BASEDIR/common-base/config/info_logging.properties
CLASSPATH=$BASEDIR/common-base/build/classes:$BASEDIR/common-daf-v2/build/classes:$CONFIGDIR:
echo $CONFIGDIR
echo $LOGFILE
echo $CLASSPATH
java -cp $CLASSPATH -Djava.util.logging.config.file=$LOGFILE  com.pb.common.daf.admin.CommandProcessor $1 $2

LOGFILE=$BASEDIR/common-base/config/info_logging.properties
CLASSPATH=$BASEDIR/common-base/build/classes:$BASEDIR/common-daf-v2/build/classes:$CONFIGDIR:
echo $CONFIGDIR
echo $LOGFILE
echo $CLASSPATH:
java -cp $CLASSPATH -Xmx1200m -Djava.util.logging.config.file=$LOGFILE -DnodeName=$1 com.pb.common.daf.admin.StartNode
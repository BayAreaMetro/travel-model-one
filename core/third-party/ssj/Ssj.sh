#!/bin/sh

if [ ! $SSJHOME ]; then
    echo "You must set SSJHOME before calling this script."
    exit
fi

export LD_LIBRARY_PATH=$SSJHOME/lib:$LD_LIBRARY_PATH
export CLASSPATH=.:$SSJHOME/lib/ssj.jar:$SSJHOME/lib/colt.jar:$CLASSPATH

function cdssj() {
   cd $SSJHOME/$1
}

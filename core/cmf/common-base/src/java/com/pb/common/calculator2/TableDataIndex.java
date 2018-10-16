package com.pb.common.calculator2;

import java.io.Serializable;

public class TableDataIndex implements Serializable {

    public int positionInList = -1;
    public int columnPosition = -1;


    TableDataIndex (int positionInList, int columnPosition) {
        this.positionInList = positionInList;
        this.columnPosition = columnPosition;
    }
}

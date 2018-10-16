package com.pb.common.calculator2;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixType;

/**
 * User: Jim
 * Date: Aug 5, 2008
 * Time: 8:30:39 AM
 * To change this template use File | Settings | File Templates.
 */
public interface MatrixDataServerIf {
    public void start32BitMatrixIoServer( MatrixType mType );
    public void stop32BitMatrixIoServer();
    Matrix getMatrix( DataEntry matrixEntry );
    public String testRemote();
    public void clear();
}


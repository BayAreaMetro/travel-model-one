package com.pb.common.calculator;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixException;
import com.pb.common.matrix.MatrixType;
import com.pb.common.calculator.DataEntry;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Aug 5, 2008
 * Time: 8:30:39 AM
 * To change this template use File | Settings | File Templates.
 */
public interface MatrixDataServerIf {
    public void start32BitMatrixIoServer( MatrixType mType );
    public void stop32BitMatrixIoServer();
    public Matrix getMatrix( DataEntry matrixEntry );
    
    public String testRemote( String remoteObjectName );
    public String testRemote();
    public void clear();
    public void writeMatrixFile(String fileName, Matrix[] m);
}


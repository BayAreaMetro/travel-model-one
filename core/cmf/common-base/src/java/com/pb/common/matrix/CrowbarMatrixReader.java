package com.pb.common.matrix;

import com.pb.crowbar.CrowbarClient;
import com.pb.crowbar.CrowbarType;

/**
 * The {@code CrowbarMatrixReader} ...
 *
 * @author crf
 *         Started 3/21/12 3:53 PM
 */
public class CrowbarMatrixReader extends MatrixReader {
    private static String DEFAULT_CROWBAR_IPADDRESS = "localhost";
    private static int DEFAULT_CROWBAR_PORT = CrowbarClient.DEFAULT_CROWBAR_PORT;

    private final CrowbarClient client;
    private final CrowbarType type;
    private final String resource;

    public static void setDefaultCrowbarIpaddress(String ipaddress) {
        DEFAULT_CROWBAR_IPADDRESS = ipaddress;
    }

    public static void setDefaultCrowbarPort(int port) {
        DEFAULT_CROWBAR_PORT = port;
    }


    public static void main(String... args) {

    }

    public CrowbarMatrixReader(String ipaddress, int port, CrowbarType type, String resource) {
        client = new CrowbarClient(ipaddress,port);
        this.type = type;
        this.resource = resource;
    }

    public CrowbarMatrixReader(String ipaddress, CrowbarType type, String resource) {
        this(ipaddress,DEFAULT_CROWBAR_PORT,type,resource);
    }

    public CrowbarMatrixReader(CrowbarType type, String resource) {
        this(DEFAULT_CROWBAR_IPADDRESS,DEFAULT_CROWBAR_PORT,type,resource);
    }

    private Matrix toMatrix(double[][] data) {
        int r = data.length;
        int c = data[0].length;
        float[][] newData =new float[r][c];
        for (int i = 0; i < r; i++)
            for (int j = 0; j < c; j++)
                newData[i][j] = (float) data[i][j];
        return new Matrix(newData);
    }

    @Override
    public Matrix readMatrix(String name) throws MatrixException {
        return toMatrix(client.getMatrixData(type,resource,client.getTableNumber(type,resource,name)));
    }

    @Override
    public Matrix readMatrix() throws MatrixException {
        throw new MatrixException("Use readMatrix(String) instead");
    }

    @Override
    public Matrix[] readMatrices() throws MatrixException {
        int matrixCount = client.getTableCount(type,resource);
        Matrix[] matrices = new Matrix[matrixCount];
        for (int i = 0; i < matrixCount; i++)
            matrices[i] = toMatrix(client.getMatrixData(type,resource,i+1));
        return matrices;
    }
}

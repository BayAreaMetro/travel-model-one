package com.pb.common.matrix;

import com.pb.crowbar.CrowbarClient;
import com.pb.crowbar.CrowbarType;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

/**
 * The {@code CrowbarMatrixWriter} ...
 *
 * @author crf
 *         Started 3/21/12 4:16 PM
 */
public class CrowbarMatrixWriter extends MatrixWriter {
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

    public CrowbarMatrixWriter(String ipaddress, int port, CrowbarType type, String resource) {
        client = new CrowbarClient(ipaddress,port);
        this.type = type;
        this.resource = resource;
    }

    public CrowbarMatrixWriter(String ipaddress, CrowbarType type, String resource) {
        this(ipaddress,DEFAULT_CROWBAR_PORT,type,resource);
    }

    public CrowbarMatrixWriter(CrowbarType type, String resource) {
        this(DEFAULT_CROWBAR_IPADDRESS,DEFAULT_CROWBAR_PORT,type,resource);
    }

    @Override
    public void writeMatrix(Matrix m) throws MatrixException {
        writeMatrix(m.getName(),m);
    }

    @Override
    public void writeMatrix(String name, Matrix m) throws MatrixException {
        writeMatrices(new String[] {name},new Matrix[] {m});
    }

    private double[][] getData(Matrix m) {
        int r = m.getRowCount();
        int c = m.getColumnCount();
        float[][] data = m.getValues();
        double[][] dData = new double[r][c];
        for (int i = 0; i < r; i++)
            for (int j = 0; j < c; j++)
                dData[i][j] = data[i][j];
        return dData;
    }

    @Override
    public void writeMatrices(String[] names, Matrix[] m) throws MatrixException {
        Map<String,double[][]> data = new HashMap<String,double[][]>();
        for (int i = 0; i < names.length; i++)
            data.put(names[i],getData(m[i]));
        client.writeMatrices(type,resource,data);
    }

    public static void main(String ... args) {
        float [][] data = new float[2402][2402];

//        data[0] = new float[] {1,2,3,4};
//        data[1] = new float[] {2,3,4,1};
//        data[2] = new float[] {3,4,1,2};
//        data[3] = new float[] {4,1,2,Float.POSITIVE_INFINITY};
        data[2401][2401] = Float.POSITIVE_INFINITY;

        Matrix m = new Matrix("test","",data);

        CrowbarMatrixWriter writer = new CrowbarMatrixWriter("192.168.1.183",5000,CrowbarType.TP_PLUS,"test.tpp");
        writer.writeMatrix(m);
    }
}

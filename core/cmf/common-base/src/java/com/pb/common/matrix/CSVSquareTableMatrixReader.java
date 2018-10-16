package com.pb.common.matrix;

import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;

/**
 * Implementes a MatrixReader to read matrices from a comma separated value file.
 * The matrix is organized by rows - with the first row being a header row which gives
 * the type of values (i.e. TIME, DIST, etc) in the first entry position, and the
 * destination zones in the subsequent entry positions.
 *
 * The second thru .... rows, have the origin zone in the first entry position and the
 * values in the subsequent entry positions.
 *
 * Currently the reader will return a single matrix.  The code assumes that the matrix
 * is square and that the external origin zone numbers = external destination zone numbers
 *
 * ex. The CSV file looks like this:
 * TIME, 1, 2, 3
 * 1,0.2,5.4,7.6
 * 2,1.1,3.5,0.7
 * 3,0.5,3.5,1.0
 *
 * The motivation for this class is to read in matrices that have been exported by TPPlus.

 *
 * @author    John Abraham
 * @version   1.0, 5/23/2006
 */
public class CSVSquareTableMatrixReader extends MatrixReader {
    
    static final Logger logger = Logger.getLogger(CSVSquareTableMatrixReader.class);

    File myDirectory;
    
    public CSVSquareTableMatrixReader(File myDirectory) {
        super();
        this.myDirectory = myDirectory;
    }

    @Override
    public Matrix[] readMatrices() throws MatrixException {
        // TODO readMatrices should read every CSV file in the directory.
        throw new RuntimeException("readMatrices not implemented, need to specify a file name");
    }

    @Override
    //TODO  This method needs to verify that the matrix is square and that the
    //TODO origin zones are the same as the destination zones.
    //TODO (Although I don't really see why you have to assume a square matrix - why not use
    //TODO the setRowExternals, setColumnExternals and allow the matrix to be non-square)
    //TODO comments by Christi Willison
    public Matrix readMatrix(String index) throws MatrixException {
        File file = new File (myDirectory.getPath() + File.separator + index + ".csv");
        BufferedReader inStream = null;
        try {
            inStream = new BufferedReader( new FileReader(file) );
        } catch (FileNotFoundException e) {
            throw new RuntimeException("Can't open file "+file);
        }
        float[][] values;
        int[] zones;
        try {
            String line =inStream.readLine();
            String[] entries = line.split(",");
            int numZones = entries.length-1;
            zones = new int[numZones];
            int maxZoneNumber = 0;
            for (int z=0;z<numZones;z++) {
                zones[z] = Integer.parseInt(entries[z+1]);
                if (zones[z] > maxZoneNumber) maxZoneNumber = zones[z];
            }
            int[] zoneNumberLookup = new int[maxZoneNumber+1];
            for (int i=0;i<zoneNumberLookup.length;i++) {
                zoneNumberLookup[i]=-1;
            }
            for (int i=0;i<zones.length;i++) {
                zoneNumberLookup[zones[i]]=i;
            }
            values = new float[numZones][numZones];
            int rowNumber = 0;
            while ((line=inStream.readLine())!=null) {
               entries = line.split(",");
               int origin = Integer.parseInt(entries[0]);
               if (++rowNumber%100==0) System.out.println("Parsing origin "+origin);
               int oIndex = zoneNumberLookup[origin];
               for (int dIndex = 0;dIndex<entries.length-1;dIndex++) {
                   values[oIndex][dIndex] = Float.parseFloat(entries[dIndex+1]);
               }
            }
            // TODO should check for missing values
        } catch (IOException e) {
            logger.error("IO Exception reading matrix");
            throw new RuntimeException("IO Exception reading matrix",e);
        } 

        Matrix m = new Matrix(index,"",values);
        m.setExternalNumbersZeroBased(zones);
        return m;
    }

    @Override
    public Matrix readMatrix() throws MatrixException {
        throw new RuntimeException("readMatrix() not implemented, need to specify a file name and use readMatrix(String)");
    }

}

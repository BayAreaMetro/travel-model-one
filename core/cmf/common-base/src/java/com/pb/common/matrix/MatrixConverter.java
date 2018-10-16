package com.pb.common.matrix;

import java.io.File;

public class MatrixConverter {

    /**
     * Converts a file (arg0) from type 1 (arg1) to file2 (arg2) of type 2 (arg3)
     * @param args
     */
    public static void main(String[] args) {
        if (args.length!=4) {
            System.out.println("usage: MatrixConverter fileIn, typeIn, fileOut, typeOut");
            System.out.println("Current valid types are Binary, ZIP, CSV, Emme2, D311, TPPlus, Transcad");
        }
        MatrixReader reader = MatrixReader.createReader(args[1], new File(args[0]));
        Matrix m = reader.readMatrix();
        MatrixWriter writer = MatrixWriter.createWriter(args[3], new File(args[2]));
        writer.writeMatrix(m);

    }

}

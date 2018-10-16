package com.pb.common.matrix.tests;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Enumeration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Created by IntelliJ IDEA.
 * User: Christi
 * Date: Jan 5, 2006
 * Time: 9:27:09 AM
 * To change this template use File | Settings | File Templates.
 */
public class UnzipFile {

    private static void doUnzipFiles(String zipFileName) {

        try {

            ZipFile zf = new ZipFile(zipFileName);

            System.out.println("Archive:  " + zipFileName);

            // Enumerate each entry
            for (Enumeration entries = zf.entries(); entries.hasMoreElements();) {

                // Get the entry and its name
                ZipEntry zipEntry = (ZipEntry)entries.nextElement();
                String zipEntryName = zipEntry.getName();

                OutputStream out = new FileOutputStream("/models/osmp/skims/unzipped/" + zipEntryName);
                InputStream in = zf.getInputStream(zipEntry);

                byte[] buf = new byte[1024];
                int len;
                String value = "";
                while((len = in.read(buf)) > 0) {
                    out.write(buf, 0, len);
                }
                
                // Close streams
                out.close();
                in.close();
            }

        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }

    }


    /**
     * Sole entry point to the class and application.
     * @param args Array of String arguments.
     */
    public static void main(String[] args) {

        if (args.length != 1) {
            System.err.println("Usage: java UnzipFile zipfilename");
        } else {
            doUnzipFiles(args[0]);
        }

    }

}

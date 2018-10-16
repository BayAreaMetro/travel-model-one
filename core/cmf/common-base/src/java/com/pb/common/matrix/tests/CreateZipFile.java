package com.pb.common.matrix.tests;

// -----------------------------------------------------------------------------
// CreateZipFile.java
// -----------------------------------------------------------------------------

/*
 * =============================================================================
 * Copyright (c) 1998-2005 Jeffrey M. Hunter. All rights reserved.
 *
 * All source code and material located at the Internet address of
 * http://www.idevelopment.info is the copyright of Jeffrey M. Hunter, 2005 and
 * is protected under copyright laws of the United States. This source code may
 * not be hosted on any other site without my express, prior, written
 * permission. Application to host any of the material elsewhere can be made by
 * contacting me at jhunter@idevelopment.info.
 *
 * I have made every effort and taken great care in making sure that the source
 * code and other content included on my web site is technically accurate, but I
 * disclaim any and all responsibility for any loss, damage or destruction of
 * data or any other property which may arise from relying on it. I will in no
 * case be liable for any monetary damages arising from such loss, damage or
 * destruction.
 *
 * As with any code, ensure to test this code in a development environment
 * before attempting to run it in production.
 * =============================================================================
 */

import com.pb.common.util.PerformanceTimer;
import com.pb.common.util.PerformanceTimerType;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * -----------------------------------------------------------------------------
 * Used to provide an example of creating a zip file.
 *
 * @version 1.0
 * @author  Jeffrey M. Hunter  (jhunter@idevelopment.info)
 * @author  http://www.idevelopment.info
 * -----------------------------------------------------------------------------
 */

public class CreateZipFile {

    private static void doCreateZipFile(String pathToFiles, String zipFileName) {


        File dir = new File(pathToFiles);
        File[] filePaths = dir.listFiles();
        String[] files = new String[filePaths.length];
        int l = 0;
        for (File file: filePaths){
            files[l] = file.getName();
            l++;
        }
        byte[] buf = new byte[16996];

        PerformanceTimer timer = PerformanceTimer.createNewTimer("ZipWriter", PerformanceTimerType.MATRIX_WRITE);
        timer.start();
        try {

            ZipOutputStream out = new ZipOutputStream(new FileOutputStream(zipFileName));

            System.out.println("Archive:  " + zipFileName);

            // Compress the files
            for (int i=1; i<files.length; i++) {

                FileInputStream in = new FileInputStream(pathToFiles + "/" + files[i]);

                out.putNextEntry(new ZipEntry(files[i]));

                // Transfer bytes from the file to the ZIP file
                int len;
                while((len = in.read(buf)) > 0) {
                    out.write(buf, 0, len);
                }

                // Complete the entry
                out.closeEntry();
                in.close();
            }

            // Complete the ZIP file
            out.close();


        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        timer.stop();
        System.out.println("Time to write all rows into the ZipMatrix: " + timer.getTotalElapsedMilliseconds());


    }


    /**
     * Sole entry point to the class and application.
     * @param args Array of String arguments.
     */
    public static void main(String[] args) {

        if (args.length < 2) {
            System.err.println("Usage: java CreateZipFile outputzipfilename filename1, filename2, ...");
        } else {
            doCreateZipFile(args[0],args[1]);
        }

    }

}



package com.pb.models.utils;

import java.io.*;
import java.util.regex.Pattern;
import java.util.Arrays;

/**
 * <p/>
 *
 * @version 1.0 Oct 12, 2007 - 8:47:14 AM
 *          </p>
 * @author crf
 */
public class CombineCsvMatrices {
    private File fileDirectory;
    private String fileFilterString;
    private String outFilter;
    private String[] indexColumns;
    private String dataColumn;

    //filter format is abce*fc* where stars are where you want wildcards (.csv is added implicitly)
    //outFilter is the format for the output file column; it uses the format fsjieij$1fdks$2 where $1 and $2 are the wildcards used in filter
    public CombineCsvMatrices(String directory,String filter,String[] indexColumns, String dataColumn, String outFilter) {
        fileDirectory = new File(directory);
        if (!fileDirectory.exists() || !fileDirectory.isDirectory()) {
            throw new IllegalArgumentException("File directory not a directory: " + directory);
        }
        this.fileFilterString = filter.replace("@","(.*)") + "[.]csv";
        this.outFilter = outFilter;
        this.indexColumns = indexColumns;
        this.dataColumn = dataColumn;
    }

    private File[] getFileList() {
        return fileDirectory.listFiles(
            new FilenameFilter() {
                public boolean accept(File dir, String name) {
                    return name.matches(fileFilterString);
                }
            }
        );
    }

    private int[] getColumnIndices(String[] columns) {
        int[] indices = new int[indexColumns.length + 1];
        outer: for (int i = 0; i < indexColumns.length; i++) {
            for (int j = 0; j < columns.length; j++) {
                if (columns[j].equals(indexColumns[i])) {
                    indices[i] = j;
                    continue outer;
                }
                if (j==columns.length) {
                    throw new IllegalStateException("Column name not found in file: " + indexColumns[i]);
                }
            }
        }
        for (int i = 0; i < columns.length; i++) {
            if (columns[i].equals(dataColumn)) {
                indices[indices.length-1] = i;
                continue;
            }
            if (i==columns.length) {
                throw new IllegalStateException("Column name not found in file: " + dataColumn);
            }
        }
        return indices;
    }

    public void combineMatrices(String outputFile) throws IOException {
        File[] fileList = getFileList();
        Arrays.sort(fileList);
        BufferedReader[] brs = new BufferedReader[fileList.length];
        int[] columnIndices = new int[0];
        String line;
        StringBuilder outLine = new StringBuilder();
        boolean first = true;
        for (String col : indexColumns) {
            if (first) {
                first = false;
                outLine.append(col);
                continue;
            }
            outLine.append(",").append(col);
        }
        for (int i = 0; i < fileList.length; i++) {
            brs[i] = new BufferedReader(new FileReader(fileList[i]));
            line = brs[i].readLine();
            if (i == 0) {
                columnIndices = getColumnIndices(line.split(","));
            }
            outLine.append(",").append(Pattern.compile(fileFilterString).matcher(fileList[i].getName()).replaceAll(outFilter));
        }

        //need to add header line
        PrintWriter pw = new PrintWriter(new BufferedWriter(new FileWriter(new File(outputFile))));
        pw.println(outLine);
        int dataIndex = columnIndices.length - 1;
//        int lineCount = 0;
        while ((line = brs[0].readLine()) != null) {
//            if (lineCount++ % 1000 == 0) {
//                System.out.println("" + (lineCount - 1) + " lines processed.");
//            }
            String[] parsedLine = line.split(",");
            outLine = new StringBuilder();
            for (int i = 0; i < columnIndices.length - 1; i++) {
                outLine.append(parsedLine[columnIndices[i]]).append(",");
            }
            outLine.append(parsedLine[columnIndices[dataIndex]]);
            for (int i = 1; i < brs.length; i++) {
                parsedLine = brs[i].readLine().split(",");
                outLine.append(",").append(parsedLine[columnIndices[dataIndex]]);
            }
            pw.println(outLine);
        }
        for (BufferedReader br : brs) {
            br.close();
        }
        pw.close();
    }

    private static String getUsage() {
        StringBuffer sb = new StringBuffer();
        sb.append("Usage: java [-classpath (classpath)] com.pb.models.utils.CombineCsvMatrices\n\t").
                append("-in (input filename)\n\t").
                append("-out (output filename)\n\t").
                append("-id (identifier columns)\n\t").
                append("-c (add column)\n\t").
                append("-cname (add column name\n\n");
        sb.append("where:\n\t").
                append("input filename is the name of the input csv files (without the extension) using @ wildcards, must include full path\n\n\t").
                append("output filename is the output file (including the extension)\n\n\t").
                append("identifier columns are the column names (comma delimited) that are shared amongst all files and are to be included in the output\n\n\t").
                append("add column is the name of the column which differs amongst the files\n\n\t").
                append("cname is the name to give each column, using $n to denote the nth wildcard from input filename\n\n");
        sb.append("example:\n\t").
                append("java com.pb.models.utils.CombineCsvMatrices -in c:/matrices/BuyingSctg@ -out c:/matrices/BuyingSctg.csv -id i,j -c matrix0 -cname BuyingSctg$1");
        return sb.toString();
    }

    public static void main(String[] args) throws IOException {
        String in = null;
        String out = null;
        String[] id = null;
        String column = null;
        String columnName = null;

        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if (arg.equals("-in")) {
                in = args[++i];
            } else if (arg.equals("-out")) {
                out = args[++i];
            } else if (arg.equals("-id")) {
                id = args[++i].split(",");
            } else if (arg.equals("-c")) {
                column = args[++i];
            } else if (arg.equals("-cname")) {
                columnName = args[++i];
            } else {
                System.out.println("Argument not recognized: " + arg);
            }
        }

        StringBuffer uninitialized = new StringBuffer();
        if (in == null)
            uninitialized.append("in\n");
        if (out == null)
            uninitialized.append("out\n");
        if (id == null)
            uninitialized.append("id\n");
        if (column == null)
            uninitialized.append("column\n");
        if (columnName == null)
            uninitialized.append("columnName\n");

        if (uninitialized.length() > 0) {
            System.out.println(getUsage());
            System.out.println("\nThe following arguments were not specfied:\n" + uninitialized.toString());
            return;
        }

        int fileNameSplit = Math.max(in.lastIndexOf("\\"),in.lastIndexOf("/"));
        String inPath = "";
        if (fileNameSplit > -1) {
            inPath = in.substring(0,++fileNameSplit);
            in = in.substring(fileNameSplit);
        }

        CombineCsvMatrices csm = new CombineCsvMatrices(inPath,in,id,column,columnName);
        csm.combineMatrices(out);

    }

}

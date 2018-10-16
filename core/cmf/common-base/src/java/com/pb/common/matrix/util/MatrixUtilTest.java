package com.pb.common.matrix.util;

import static org.junit.Assert.*;
import junit.framework.JUnit4TestAdapter;
import org.apache.log4j.Logger;
import org.junit.BeforeClass;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixWriter;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.TableDataFileWriter;
import com.pb.common.datafile.FileType;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Scanner;
import java.util.ArrayList;

/**
 *
 * Test the MatrixUtil class (and some other stuff along the way).
 *
 * To test this, the following matrix will be used:
 *
 * <table border=0>
 *     <tr align="center">
 *         <th>Zone</th>
 *         <td>&nbsp;</td>
 *         <td><b>101</b></td>
 *         <td><b>102</b></td>
 *         <td><b>103</b></td>
 *         <td><b>104</b></td>
 *         <td><b>105</b></td>
 *     </tr>
 *     <tr align="center">
 *         <th>101</th>
 *         <td></td>
 *         <td>1</td>
 *         <td>2</td>
 *         <td>3</td>
 *         <td>4</td>
 *         <td>5</td>
 *     </tr>
 *     <tr align="center">
 *         <th>102</th>
 *         <td></td>
 *         <td>1</td>
 *         <td>3</td>
 *         <td>5</td>
 *         <td>7</td>
 *         <td>9</td>
 *     </tr>
 *     <tr align="center">
 *         <th>103</th>
 *         <td></td>
 *         <td>0</td>
 *         <td>2</td>
 *         <td>4</td>
 *         <td>6</td>
 *         <td>8</td>
 *     </tr>
 *     <tr align="center">
 *         <th>104</th>
 *         <td></td>
 *         <td>1</td>
 *         <td>1</td>
 *         <td>2</td>
 *         <td>3</td>
 *         <td>5</td>
 *     </tr>
 *     <tr align="center">
 *         <th>105</th>
 *         <td></td>
 *         <td>9</td>
 *         <td>8</td>
 *         <td>7</td>
 *         <td>0</td>
 *         <td>0</td>
 *     </tr>
 * </table>
 * <br />
 * 
 * The alpha to beta correspondences is as follows:
 * <br />
 * <br />
 * <table border=1 style="border-collapse: collapse">
 *     <tr align="center">
 *         <th>Alpha</th>
 *         <th>Beta</th>
 *     </tr>
 *     <tr align="center">
 *         <td>101</td>
 *         <td>201</td>
 *     </tr>
 *     <tr align="center">
 *         <td>102</td>
 *         <td>202</td>
 *     </tr>
 *     <tr align="center">
 *         <td>103</td>
 *         <td>202</td>
 *     </tr>
 *     <tr align="center">
 *         <td>104</td>
 *         <td>201</td>
 *     </tr>
 *     <tr align="center">
 *         <td>105</td>
 *         <td>203</td>
 *     </tr>
 * </table>
 * <br />
 * <br />
 * User: Chris               <br/>
 * Date: May 29, 2007 - 10:05:31 AM
 */
public class MatrixUtilTest {
     public static junit.framework.Test suite() {
           return new JUnit4TestAdapter(MatrixUtilTest.class);
       }

    static Logger logger = Logger.getLogger(MatrixUtilTest.class);

//    private static final File testDir = new File(MatrixUtilTest.class.getResource("MatrixUtilTest.class").toExternalForm().
//                        replace("file:/","").replace("MatrixUtilTest.class",""));
    private static final File testDir = new File("./");
    static private File testMatrixFile;
    static private File outputFile;
    static private File a2bFile;
    static float[] row1;
    static float[] row2;
    static float[] row3;
    static float[] row4;
    static float[] row5;
    static int[] externalNumbers;


    @BeforeClass
    public static void oneTimeSetUp() {
        //create test matrix
        row1 = new float[] {1.0f,2.0f,3.0f,4.0f,5.0f};
        row2 = new float[] {1.0f,3.0f,5.0f,7.0f,9.0f};
        row3 = new float[] {0.0f,2.0f,4.0f,6.0f,8.0f};
        row4 = new float[] {1.0f,1.0f,2.0f,3.0f,5.0f};
        row5 = new float[] {9.0f,8.0f,7.0f,0.0f,0.0f};
        externalNumbers = new int[] {0,101,102,103,104,105};
        Matrix testMatrix = new Matrix("TestMatrix","A matrix to test with",new float[][] {row1,row2,row3,row4,row5});
        testMatrix.setExternalNumbers(externalNumbers);
        testMatrixFile = new File(testDir.toString() + "\\TestMatrix.zmx");
        MatrixWriter.createWriter(MatrixType.ZIP,testMatrixFile).writeMatrix(testMatrix);

        //create output file object
        outputFile = new File(testDir.toString() + "\\OutputTest.csv");

        //create alpha2beta file
        String[] abNames = new String[] {"Alpha","Beta"};
        TableDataSet alpha2BetaData = TableDataSet.create(
                new float[][] {{101,201},
                               {102,202},
                               {103,202},
                               {104,201},
                               {105,203}},abNames);
        a2bFile = new File(testDir.toString() + "\\Alpha2Beta.csv");
        try {
            TableDataFileWriter.createWriter(FileType.CSV).writeFile(alpha2BetaData,a2bFile);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

    }

    @AfterClass
    public static void oneTimeTearDown() {
        deleteFile(testMatrixFile,10);
        deleteFile(a2bFile,10);

    }

    @Before
    public void setUp() {

    }

    @After
    public void tearDown() throws Exception{
        //have to try a couple of times to get the files to delete
        deleteFile(outputFile,10);
    }

    private static void deleteFile(File file, int maxTries) {
       //stupid java may have some bizarre file lock somewhere
        int counter = 0;
        while(counter++ < maxTries && !file.delete()) {}
    }

    private void runMatrixUtil(String ... commandLine) {
        MatrixUtil.main(commandLine);
    }

    private void runStandardMatrixUtil(String ... matrixCommands) {
        String[] commandLine = new String[matrixCommands.length + 4];
        commandLine[0] = "--mat";
        commandLine[1] = testMatrixFile.toString();
        commandLine[2] = "--out";
        commandLine[3] = outputFile.toString();
        int counter = 4;
        for (String command : matrixCommands) {
            commandLine[counter++] = command;
        }
        runMatrixUtil(commandLine);
    }

    private String readFile(File file) {
        String text;
        try {
            Scanner s = new Scanner(file);
            text = s.useDelimiter("\\A").next();
            s.close();
        } catch (FileNotFoundException e) {
            e.printStackTrace();
            text = "";
        }
        return text;
    }

    private String cleanLineBreaksAndSpaces(String in) {
        return in.replaceAll("[\\n\\r ]","");
    }

    private boolean equalMatrices(Matrix m1, Matrix m2) {
        boolean equal = false;
        if (m1.getRowCount() == m2.getRowCount()) {
            if (m1.getColumnCount() == m2.getColumnCount()) {
                int[] rows = m1.externalRowNumbers;
                int[] columns = m1.externalColumnNumbers;
                outer:
                    for (int i = 1; i < rows.length; i++) {
                        for (int j = 1; j < columns.length; j++) {
                            try {
                                if (m1.getValueAt(rows[i],columns[j]) != m2.getValueAt(rows[i],columns[j]))
                                    break outer;
                            } catch (Exception e) {
                                e.printStackTrace();
                                break outer;
                            }
                        }
                        if (i== rows.length - 1)
                            equal = true;
                    }
            }
        }

        return equal;
    }

    /**
     * This tests whether the write method (--mat and --out with no other mainArgs) works.
     * The comparison string is built up from scratch, but is compared without line breaks or spaces, so it should be
     * platform/formatting independent.
     */
    @Test
    public void testReadWrite() {
        runStandardMatrixUtil();
        //This is what the output file should look like
        String csvOut = "i,j,TestMatrix\n " +
                "101,101,1.0\n 101,102,2.0\n 101,103,3.0\n 101,104,4.0\n 101,105,5.0\n" +
                "102,101,1.0\n 102,102,3.0\n 102,103,5.0\n 102,104,7.0\n 102,105,9.0\n" +
                "103,101,0.0\n 103,102,2.0\n 103,103,4.0\n 103,104,6.0\n 103,105,8.0\n" +
                "104,101,1.0\n 104,102,1.0\n 104,103,2.0\n 104,104,3.0\n 104,105,5.0\n" +
                "105,101,9.0\n 105,102,8.0\n 105,103,7.0\n 105,104,0.0\n 105,105,0.0\n";
        
        assertEquals(cleanLineBreaksAndSpaces(csvOut),cleanLineBreaksAndSpaces(readFile(outputFile)));
    }

    /**
     * This tests whether getting a row from a matrix works.
     */
    @Test
    public void testSubRow() {
        runStandardMatrixUtil("--subMatrix","-row","101");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] oneExternal = new int[2];
        System.arraycopy(externalNumbers,0,oneExternal,0,2);
        Matrix m2 = new Matrix(new float[][] {row1});
        m2.setExternalNumbers(oneExternal,externalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    /**
     * This tests whether getting a column from a matrix works.
     */
    @Test
    public void testSubCol() {
        runStandardMatrixUtil("--subMatrix","-col","101");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] oneExternal = new int[2];
        System.arraycopy(externalNumbers,0,oneExternal,0,2);
        float[] newRow1 = new float[1];
        float[] newRow2 = new float[1];
        float[] newRow3 = new float[1];
        float[] newRow4 = new float[1];
        float[] newRow5 = new float[1];
        System.arraycopy(row1,0,newRow1,0,1);
        System.arraycopy(row2,0,newRow2,0,1);
        System.arraycopy(row3,0,newRow3,0,1);
        System.arraycopy(row4,0,newRow4,0,1);
        System.arraycopy(row5,0,newRow5,0,1);
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3,newRow4,newRow5});       
        m2.setExternalNumbers(externalNumbers,oneExternal);
        assertEquals(true,equalMatrices(m1,m2));
    }

    /**
     * This tests whether getting a square submatrix works. It tests it using the "dash" (X-Y) notation.
     */
    @Test
    public void testSquareSubmatrix() {
        runStandardMatrixUtil("--subMatrix","-rowcol","101-103");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = new int[4];
        float[] newRow1 = new float[3];
        float[] newRow2 = new float[3];
        float[] newRow3 = new float[3];
        System.arraycopy(externalNumbers,0,newExternalNumbers,0,4);
        System.arraycopy(row1,0,newRow1,0,3);
        System.arraycopy(row2,0,newRow2,0,3);
        System.arraycopy(row3,0,newRow3,0,3);
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    /**
     * This test whether getting a square submatrix works.  It uses the list notation.
     */
    @Test
    public void testSquareSubmatixList() {
        runStandardMatrixUtil("--subMatrix","-rowcol","102","103","101");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = new int[4];
        float[] newRow1 = new float[3];
        float[] newRow2 = new float[3];
        float[] newRow3 = new float[3];
        System.arraycopy(externalNumbers,0,newExternalNumbers,0,4);
        System.arraycopy(row1,0,newRow1,0,3);
        System.arraycopy(row2,0,newRow2,0,3);
        System.arraycopy(row3,0,newRow3,0,3);
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));

    }

    /**
     * This tests nested submatrix commands. It implicitly tests a mixing of -rowcol, -col, and -row, as well as a
     * mixing of dash (X-Y) and list number formats.
     */
    @Test
    public void testNestedSubmatrix() {
        runStandardMatrixUtil("--subMatrix","-rowcol","101-103","--subMatrix","-row","101","102","-col","101-102");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = new int[3];
        float[] newRow1 = new float[2];
        float[] newRow2 = new float[2];
        System.arraycopy(externalNumbers,0,newExternalNumbers,0,3);
        System.arraycopy(row1,0,newRow1,0,2);
        System.arraycopy(row2,0,newRow2,0,2);
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    /**
     * This tests nested submatrix commands. In this case, it does a subrow, then a subcol, and then a subrow, and
     * should end with a square submatrix.
     */
    @Test
    public void testNestedSubmatrix2() {
        runStandardMatrixUtil("--subMatrix","-row","101-103","--subMatrix","-col","101","102","--subMatrix","-row","101-102");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = new int[3];
        float[] newRow1 = new float[2];
        float[] newRow2 = new float[2];
        System.arraycopy(externalNumbers,0,newExternalNumbers,0,3);
        System.arraycopy(row1,0,newRow1,0,2);
        System.arraycopy(row2,0,newRow2,0,2);
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    private boolean alpha201Submatrix(String ... args) {
        runStandardMatrixUtil(args);
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = new int[3];
        float[] newRow1 = new float[2];
        float[] newRow2 = new float[2];
        newExternalNumbers[1] = 101;
        newExternalNumbers[2] = 104;
        newRow1[0] = row1[0];
        newRow1[1] = row1[3];
        newRow2[0] = row4[0];
        newRow2[1] = row4[3];
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2});
        m2.setExternalNumbers(newExternalNumbers);
        return equalMatrices(m1,m2);
    }

    /**
     * Tests a basic submatrix generated from a file.
     */
    @Test
    public void testSubmatrixFromFile1() {
        assertEquals(true,
                alpha201Submatrix("--subMatrix","-file",a2bFile.toString(),"-rowcol","Alpha","-filter","Beta","-class","201"));
    }

    /**
     * Tests a submatrix generated from a file with all of the arguments spelled out as rowcol.
     */
    @Test
    public void testSubmatrixFromFile2() {
        assertEquals(true,
                alpha201Submatrix("--subMatrix","-rowcolfile",a2bFile.toString(),"-rowcol","Alpha","-rowcolfilter","Beta","-rowcolclass","201"));
    }

    /**
     * Tests a submatrix generated from a file with all of the arguments split into row/col.
     */
    @Test
    public void testSubmatrixFromFile3() {
        assertEquals(true,
                alpha201Submatrix("--subMatrix","-rowfile",a2bFile.toString(),"-row","Alpha","-rowfilter","Beta","-rowclass","201"
                        ,"-colfile",a2bFile.toString(),"-col","Alpha","-colfilter","Beta","-colclass","201"));
    }

    @Test
    public void testSqueezematrixSum() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","sum");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = {0,201,202,203};
        float[] newRow1 = {9.0f,8.0f,10.0f};
        float[] newRow2 = {14.0f,14.0f,17.0f};
        float[] newRow3 = {9.0f,15.0f,0.0f};
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    @Test
    public void testSqueezematrixMin() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","min");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = {0,201,202,203};
        float[] newRow1 = {1.0f,1.0f,5.0f};
        float[] newRow2 = {0.0f,2.0f,8.0f};
        float[] newRow3 = {0.0f,7.0f,0.0f};
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    @Test
    public void testSqueezematrixMax() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","max");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = {0,201,202,203};
        float[] newRow1 = {4.0f,3.0f,5.0f};
        float[] newRow2 = {7.0f,5.0f,9.0f};
        float[] newRow3 = {9.0f,8.0f,0.0f};
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    @Test
    public void testSqueezematrixMean() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","mean");
        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
        int[] newExternalNumbers = {0,201,202,203};
        float[] newRow1 = {9.0f/4.0f,2.0f,5.0f};
        float[] newRow2 = {14.0f/4.0f,14.0f/4.0f,17.0f/2.0f};
        float[] newRow3 = {9.0f/2.0f,15.0f/2.0f,0.0f};
        Matrix m2 = new Matrix(new float[][] {newRow1,newRow2,newRow3});
        m2.setExternalNumbers(newExternalNumbers);
        assertEquals(true,equalMatrices(m1,m2));
    }

    public void rolfsSqueeze() {
        String matrixFilePath = "C:\\models\\osmp\\scenario_00_Base\\t0\\pt\\";
        String matrixFileName1 = "carPkDist.zmx";
        String matrixFileName2 = "carPkDistAMZ.zmx";

        String a2bFile = "C:\\models\\osmp\\scenario_seam\\reference\\TAZtoAMZNew.csv";

        ArrayList<String> commandLine = new ArrayList<String>();
        commandLine.add("--mat");
        //commandLine.add(matrixFilePath + matrixFileName2);
        commandLine.add(matrixFilePath + matrixFileName1);
        commandLine.add("--out");
        //commandLine.add(matrixFilePath + "countyDistanceFromAMZ.csv");
        commandLine.add(matrixFilePath + "countyDistanceFromTAZ.csv");
        commandLine.add("--squeezeMatrix");
        commandLine.add("-file");
        commandLine.add(a2bFile);
        commandLine.add("-alpha");
        //commandLine.add("AMZ");
        commandLine.add("TAZ");
        commandLine.add("-beta");
        commandLine.add("SCFIPS");
        commandLine.add("-squeeze");
        commandLine.add("mean");

        runMatrixUtil(commandLine.toArray(new String[commandLine.size()]));
    }

    //Fails - matrix compression can't handle rectangular matrices
//    @Test
//    public void testSqueezeRectangularMatrix() {
//        runStandardMatrixUtil("--subMatrix","-row","101-102","--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","mean");
//        Matrix m1 = MatrixReader.readMatrix(outputFile,"");
//        int[] newExternalNumbers = {0,201,202,203};
//        Matrix m2 = new Matrix(new float[][] {{2,3,0},{1,5,0},{9,8,0}});
//        m2.setExternalNumbers(newExternalNumbers);
//        assertEquals(true,equalMatrices(m1,m2));
//    }



    /**
     * The following tests cover poorly formed input lines.
     */
      //Too much output on this one
//    @Test
//    public void testMalformedLine1() {
//        runMatrixUtil();
//        assertEquals(false,outputFile.exists());
//    }

    @Test
    public void testMalformedLine2() {
        runStandardMatrixUtil("--notAnArgument");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine3() {
        runStandardMatrixUtil("--subMatrix");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine4() {
        runStandardMatrixUtil("--subMatrix","-file",a2bFile.toString(),"-rowcol","Alpha","-rowfilter","Beta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test (expected=RuntimeException.class)
    public void testMalformedLine5() {
        runStandardMatrixUtil("--subMatrix","-row","h");
        assertEquals(false,outputFile.exists());
    }

    @Test 
    public void testMalformedLine6() {
        runStandardMatrixUtil("--subMatrix","-file",a2bFile.toString(),"AnotherFile.txt","-rowcol","Alpha","-filter","Beta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test (expected=RuntimeException.class)
    public void testMalformedLine7() {
        runStandardMatrixUtil("--subMatrix","-file",a2bFile.toString(),"-rowcol","Alpha","-filter","Beeta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test (expected=RuntimeException.class)
    public void testMalformedLine8() {
        runStandardMatrixUtil("--subMatrix","-file",a2bFile.toString() + "p","-rowcol","Alpha","-filter","Beeta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine9() {
        runStandardMatrixUtil("--mat",testMatrixFile.toString(),"--subMatrix","-file",a2bFile.toString() + "p","-rowcol","Alpha","-filter","Beeta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine10() {
        runStandardMatrixUtil("--out",outputFile.toString(),"--subMatrix","-file",a2bFile.toString() + "p","-rowcol","Alpha","-filter","Beeta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test 
    public void testMalformedLine11() {
        runStandardMatrixUtil("--type","CSV","--type","ZIP","--subMatrix","-file",a2bFile.toString() + "p","-rowcol","Alpha","-filter","Beeta","-class","201");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine12() {
        runStandardMatrixUtil("--squeezeMatrix");
        assertEquals(false,outputFile.exists());
    }

    @Test
    public void testMalformedLine13() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze");
        assertEquals(false,outputFile.exists());
    }

    @Test (expected=RuntimeException.class)
    public void testMalformedLine14() {
        runStandardMatrixUtil("--squeezeMatrix","-file",a2bFile.toString(),"-alpha","Alpha","-beta","Beta","-squeeze","deuce");
        assertEquals(false,outputFile.exists());
    }


    public static void main(String[] args) {
        //org.junit.runner.JUnitCore.main("com.pb.common.matrix.util.MatrixUtilTest");
        MatrixUtilTest test = new MatrixUtilTest();
        test.rolfsSqueeze();
    }
}
/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.emme2.io;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.CharBuffer;
import java.nio.channels.FileChannel;
import org.apache.log4j.Logger;

/** Represents an Emme/2 databank.
 * 
 * Originally written in C by Tim Heier and then ported to Java
 * by Joel Freedman.
 *
 * Note: Versions older than 9.0 are not yet supported.
 * Updated to read up to 3.4 banks.  Note that 4.0 banks will be 
 * significantly different and EMME Modeller is recommended for I/O.
 *
 * @author    Tim Heier, Joel Freedman, Ben Stabler
 */
public class Emme2DataBank {

    protected static Logger logger = Logger.getLogger("com.pb.common.emme2.io");

    //Helper constants
    public static int MS = 1;
    public static int MO = 2;
    public static int MD = 3;
    public static int MF = 4;

    public static int NTYPE = 5;
    public static int NMAT  = 999;
    public static int NFILE = 100;

    File file;                 //fully qualified file name of databank
    RandomAccessFile eptr;     //file pointer to databank
    boolean readOnly;          //determine if we can modify the databank
    FileChannel fc;            //file channel to the databank

    String projectTitle;       //databank title

    int maxZones;              //number of zones dimensioned
    int zonesUsed;             //number of zones used - often < dimensioned
    int highestZone;           //highest zone number used
    int maxScenarios;          //number of scenarios dimensioned
    int maxNodes;              //number of nodes dimensioned
    int maxLinks;              //number of links dimensioned
    int maxMatrices;           //number of matrices dimensioned
    int maxLines;              //number of transit lines dimensioned
    int scenMaxCents;          //scenario with highest number of centroids

    int[][] matrixFlags;       //matrix flags
    int[][] matrixTime;        //matrix timestamp
    String[] matrixName;       //matrix name
    String[] matrixDesc;       //matrix description

    /* external centroid numbers, use like this:
     * extern_cent[position] = external number
     */
    int[] externCent;

    /* internal centroid position, use like this:
     * intern_cent[cent #] = internal number
     */
    int[] internCent;

    GlobalDatabankParameters global;
    Emme2FileParameters[] ifile;


    public Emme2DataBank(String fileName) throws IOException {
        this( new File(fileName), false );
    }


    public Emme2DataBank(File file) throws IOException {
        this(file, false);
    }


    public Emme2DataBank(File file, boolean readOnly) throws IOException {
        this.file = file;
        this.readOnly = readOnly;

        global = new GlobalDatabankParameters();

        ifile = new Emme2FileParameters[100];
        for (int i = 0; i < ifile.length; ++i) {
            ifile[i] = new Emme2FileParameters();
        }

        //Determine the file mode
        String mode = "rw";
        if (readOnly) {
            mode = "r";
        }

        logger.debug( "Opening databank: " + file );

        try {
            this.eptr = new RandomAccessFile( file, mode );
            this.fc = eptr.getChannel();
        }
        catch (IOException e) {
            logger.error( "Error opening: " + file );
            throw e;
        }

        readFile0();
    }


    /** This function opens the emme2ban file and then attempts to
     * read the contents of file 0 and the global data.\
     */
    private void readFile0 () throws IOException {
        try {
            readGlobalData();
        } 
        catch (IOException e) {
            logger.error( "Error reading global data for: " + file );
            throw e;
        }
    }


    /** Closes the emme2ban file and cleans up any memory structures.
     */
    public void close() throws IOException {
        this.fc.close();
    }


    /** Reads the global data after reading the contents of file 0.
     */
    protected void readGlobalData() throws IOException {

        int  file1_begin;
        int  i, type, mat;
        int  ncent;
        long byteoff;
        int num_files;
        byte[] word4 = new byte[4];


        /* Read the first word of the databank */
        eptr.seek(0);
        eptr.read(word4,0,4);
        num_files=eptr.readInt();

        /* Detect which version of File 0 structure to read */
        if (word4[0] == 99 && (word4[1]+word4[2]+word4[3])==0) {
        	
            // < version 9
            readOldFile0();
            file1_begin = 200 * 4;
            
        } else {
        	
            // >= version 9  and < EMME 4 
            readNewFile0();   
            file1_begin = (int) ifile[1].offset;
            logger.debug("File1 Begins at "+file1_begin);

        }

        /* Global parameters are in File 1 */
        eptr.seek(file1_begin);


        /* Logical device numbers 200 - 209 */
        eptr.read(word4);
        global.LDI =convertWord4ToInt(word4);
        eptr.read(word4);
        global.LDO =convertWord4ToInt(word4);
        eptr.read(word4);
        global.LGI =convertWord4ToInt(word4);
        eptr.read(word4);
        global.LGO =convertWord4ToInt(word4);
        eptr.read(word4);
        global.LDAI=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LDAO=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LERO=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LLIO=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LREP=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LGRAPH=convertWord4ToInt(word4);

        /* Physical device numbers 210 - 219 */
        eptr.read(word4);
        global.IPHYS[1]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[2]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[3]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[4]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[5]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[6]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[7]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[8]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[9]=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPHYS[10]=convertWord4ToInt(word4);

        /* Miscellaneous parameters 220 - 249 */
        eptr.read(word4);
        global.KMOD=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDEV=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ISHORT=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LPSIZ=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IPGE=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDAT=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IUSR=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ITPTER=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ITPPRI=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ITPPLO=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM31=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM32=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IGCMD=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ICPDAT=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ISCEN=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IMODL=convertWord4ToInt(word4);
        eptr.read(word4);
        global.LMODL=convertWord4ToInt(word4);
        eptr.read(word4);
        global.ICGM=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IMFB=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IEROP=convertWord4ToInt(word4);
        eptr.read(word4);
        global.KLU=convertWord4ToInt(word4);
        eptr.read(word4);
        global.KCU=convertWord4ToInt(word4);
        eptr.read(word4);
        global.KEU=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM44=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM45=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM46=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM47=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM48=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDM49=convertWord4ToInt(word4);
        eptr.read(word4);
        global.IDBREL=convertWord4ToInt(word4);

        /* Data bank dimensions 250 - 259 */
        eptr.read(word4);
        global.MSCEN=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MCENT=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MNODE=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MLINK=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MTURN=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MLINE=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MLSEG=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MMAT=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MFUNC=convertWord4ToInt(word4);
        eptr.read(word4);
        global.MOPER=convertWord4ToInt(word4);

        /* Fill Emme2Handle strucutre with global parameter values */

        this.maxScenarios = global.MSCEN;
        this.maxZones     = global.MCENT;
        this.maxNodes     = global.MNODE;
        this.maxLinks     = global.MLINK;
        this.maxLines     = global.MLINE;
        this.maxMatrices  = global.MMAT;


        /****** File 1: Global and Scenario Parameters */

        /* Check number of centroids used versus dimensioned - keep track of
         * scenario with highest number of centroids
         */

        /* Loop through the global parameters for each scenario and read the
         * number of centroids used - also keep track of which scenario has
         * the most centroids
         */

        this.zonesUsed = 0;
        this.scenMaxCents = 1;

        for (i=1; i <= global.MSCEN; i++) {
            byteoff = file1_begin + (i*80*4);
            eptr.seek(byteoff);
            eptr.read(word4);
            ncent=convertWord4ToInt(word4);

            if (ncent > this.zonesUsed) {
                this.zonesUsed = ncent;
                this.scenMaxCents = i;
            }
        }

        /****** File 6: External Node Numbers */

        /* Read centroid number index for non-continuous zone numberinglobal.
         *
         * Read the centroid numbers from the scenario which used the
         * greatest number of cetroids.
         *
         *  extern_cent:  given a position in the zonal array - return the actual zone number
         *  intern_cent:  given an actual zone number - return position in the zonal array
         *
         *  example: centroids 3,4,6 are skipped:
         *
         *  extern_cent:  intern_cent:
         *   pos    ext    pos    int
         *     1      1      1      1
         *     2      2      2      2
         *     3      5      3      0
         *     4      7      4      0
         *                   5      3
         *                   6      0
         *                   7      4
         */

        /* Store external zone number in this pass - do this in two steps to get
         * the highest zone number used */

        this.externCent = new int[global.MCENT+1];

        byteoff = ifile[6].offset +
                  ((this.scenMaxCents-1) * ifile[6].reclen);
        eptr.seek(byteoff);

        //Find the highest zone number
        for (i=1; i <= global.MCENT; i++) {
            eptr.read(word4);
            ncent=convertWord4ToInt(word4);

            if (ncent>0) {
                this.externCent[i] = ncent;
            }
            if (ncent > this.highestZone) {
                this.highestZone = ncent;
            }
        }

        /* Store internal position number for a centroid in this pass */

        this.internCent = new int[this.highestZone+1];

        byteoff = ifile[6].offset + ((this.scenMaxCents-1) * ifile[6].reclen);
        eptr.seek(byteoff);

        for (i=1; i <= global.MCENT; i++) {
            eptr.read(word4);
            ncent=convertWord4ToInt(word4);
            if (ncent>0)
                this.internCent[ncent] = i;
        }

        if (logger.isDebugEnabled()) {
            logger.debug("");
            logger.debug("Max Scen:      "+this.maxScenarios);
            logger.debug("Max Zones:     "+this.maxZones    );
            logger.debug("Zones Used:    "+this.zonesUsed   );
            logger.debug("Highest Zone:  "+this.highestZone );
            logger.debug("Max Nodes:     "+this.maxNodes    );
            logger.debug("Max Links:     "+this.maxLinks    );
            logger.debug("Max Lines:     "+this.maxLines    );
            logger.debug("Max Matrices:  "+this.maxMatrices );
        }

        /* Print centroid zone numbering equivalence */
        if (logger.isDebugEnabled()) {
            logger.debug("");
            logger.debug("External Zone Numbering:");
            for (i=1; i <= this.zonesUsed; i++)
                logger.debug( " "+i+" "+this.externCent[i]);

            logger.debug("");
            logger.debug("Internal Postion Numbering:");
            for (i=1; i <= this.highestZone; i++)
                logger.debug( " "+i+" "+this.internCent[i]);
        }

        /****** File 60: Matrix Directory */

        /* Read matrix directory information to determine matrix availability.
         *
         * Values are stored in this order:
         * cflag(mmat,4)
         * itimst(mmat,4)
         * name(3,mmat,4)
         * descr(20,mmat,4)
         *
         * cflag is packed:
         * bit 0  matrix is defined
         * bit 1  matrix is columnwise
         * bit 2  matrix is read-only
         * bit 3  matrix is shareable read-only stored externally (not implemented)
         *
         */

        //Create array for matrix flags
        this.matrixFlags = new int[NTYPE+1][global.MMAT+1];
        this.matrixTime  = new int[NTYPE+1][global.MMAT+1];

        byteoff = ifile[60].offset;
        eptr.seek( byteoff );

        //Read cflag
        for (type=1; type < NTYPE; type++) {
            for (mat=1; mat <= global.MMAT; mat++) {
                eptr.read(word4);
                this.matrixFlags[type][mat]=convertWord4ToInt(word4);
            }
        }

        //Read itimst
        for (type=1; type < NTYPE; type++) {
            for (mat=1; mat <= global.MMAT; mat++) {
                eptr.read(word4);
                this.matrixTime[type][mat]=convertWord4ToInt(word4);
            }
        }

        //TODO fix reading matrix name/description
/*
        byte[] word6 = new byte[6];

        //Read name
        for (type=1; type < NTYPE; type++) {
            if (type == 4) {
                for (mat=1; mat <= global.MMAT; mat++) {
                    eptr.read(word6);
                    this.matrixName[mat]=convertByteArrayToString(word6);
                }
            }
        }

        byte[] word40 = new byte[40];

        //Read description
        for (type=1; type < NTYPE; type++) {
            if (type == 4) {
                for (mat=1; mat <= global.MMAT; mat++) {
                    eptr.read(word40);
                    this.matrixDesc[mat]=convertByteArrayToString(word40);
                }
            }
        }
*/
        printMatrixDirectory();

    }


    /** Reads the old  two word directory structure. This structure is made
     * up of 198 32-bit words which contain 23-bit values packed into 32-bit
     * words.  It's a little messy.
     */
    protected void readOldFile0() throws IOException {

        int ifn, byteoff1 ,byteoff2;
        int word1, bits0_27, bit28;
        int word2, bits0_20, bit21, bit22;


        logger.debug( "Reading old file directory structure" );

        /* Read two word file directory table and unpack bits */
        for (ifn=1; ifn <= 99; ifn++) {
            byteoff1 = ifn * 4;
            byteoff2 = (ifn+100) * 4;

            byte[] word4 = new byte[4];
            /* read word 1 */
            eptr.seek( byteoff1 );
            eptr.read( word4 );
            word1 = convertWord4ToInt( word4 );

            /* read word 2 */
            eptr.seek( byteoff2 );
            eptr.read( word4 );
            word2 = convertWord4ToInt( word4 );

            /****** Internal File Offsets (in bytes)
             *
             * 1. Extract bits 0-27 from word1.
             *    - 0x0FFFFFFF = "0000 1111 1111 1111 1111 1111 1111 1111"
             * 2. Shift bit 31 into position 28 and mask it so only bit 28
             *    is used.
             *    - word1 >> 3 shifts bit 31 into position 28
             *    - 0x10000000 = "0001 0000 0000 0000 0000 0000 0000 0000"
             * 3. Combine the components into the final value.
             */
            bits0_27 = word1 & 0x0FFFFFFF;
            bit28    = (word1 >> 3) & 0x10000000;

            ifile[ifn].offset = (bit28 + bits0_27) * 4;

            /****** Internal File Type
             * 
             * Type 1 -  Integer
             *      2 -  Real
             *      3 -  Text
             *
             * 1. Shift bits 28,29 to far right and mask left most bits.
             *    - word1 >> 28
             *    - 0x00000003 = "0000 0000 0000 0000 0000 0000 0000 0011"
             */
            ifile[ifn].type = (word1 >> 28) & 0x00000003;

            /****** Words per Record (record length in bytes)
             *
             * 1. Extract bits 0-20 from word2.
             *    - 0x001FFFFF = "0000 0000 0001 1111 1111 1111 1111 1111"
             * 2. Shift bit 31 from word2 into position 21 and mask it so
             *    only bit 21 is used.
             *    - word2 >> 10 shifts bit 31 into position 21
             *    - 0x00200000 = "0000 0000 0010 0000 0000 0000 0000 0000"
             * 3. Shift bit 30 from word1 into position 22 and mask it so
             *    only bit 22 is used.
             *    - word1 >> 8 shifts bit 30 into position 22
             *    - 0x00400000 = "0000 0000 0100 0000 0000 0000 0000 0000"
             * 4. Combine the components into the final value.
             */
            bits0_20 = word2 & 0x001FFFFF;
            bit21    = (word2 >> 10) & 0x00200000;
            bit22    = (word1 >> 8)  & 0x00400000;

            ifile[ifn].reclen = (bit22 + bit21 + bits0_20) * 4;

            /****** Records per File
             *
             * 1. Shift bits 21,30 from word2 to far right and mask left
             *    most bits.
             *    - word2 >> 21  "0111 1111 1110 0000 0000 0000 0000 0000"
             *    - 0x000003FF = "0000 0000 0000 0000 0000 0011 1111 1111"
             */

            ifile[ifn].nrecs = (word2 >> 21) & 0x000003FF;

        } /* for ifn */

        //Print out file directory information
        logger.debug("data bank directory format: old, with 23 bit record length");
        printRecordTable();

    }


    /** Read the new directory structure. This structure is made up
     * of 32-bit words like the old structure with no packing.
     */
    protected void readNewFile0() throws IOException {

        int  ifn;


        logger.debug( "Reading new file directory structure" );

        /* Read internal file tables in this order:
         *
         * word   0 -
         * word   1 -  99  File offsets
         * word 100 -  
         *
         * word 101 - 199  Number of records/file
         * word 200 - 
         *
         * word 201 - 299  Words/record
         * word 300 - 
         *
         * word 301 - 399  Record Type
         * word 400 - 
         */

        //Read 4-byte words
        byte[] word4 = new byte[4];

        /* Start reading at word 1 */
        eptr.seek (4);

        /* Words 1-99 */
        for (ifn=1; ifn <= 99; ifn++) {
            eptr.read(word4);
            ifile[ifn].offset=(long)convertWord4ToInt(word4)*4;

        }
        eptr.readInt();

        /* Words 101-199 */
        for (ifn=1; ifn <= 99; ifn++) {
            eptr.read(word4);
            ifile[ifn].nrecs=convertWord4ToInt(word4);
        }
        eptr.readInt();

        /* Words 201-299 */
        for (ifn=1; ifn <= 99; ifn++) {
            eptr.read(word4);
            ifile[ifn].reclen=convertWord4ToInt(word4)*4;
        }
        eptr.readInt();

        /* Words 301-399 */
        for (ifn=1; ifn <= 99; ifn++) {
            eptr.read(word4);
            ifile[ifn].type=convertWord4ToInt(word4);
        }

        /* degub - print out file directory information */
        logger.debug("data bank directory format: 32-bit");
        printRecordTable();

    }


    /** Accepts a 4-element byte array and converts to long value based on 
     * native byte order (little vs big endian). Returns long value.
     */
    public long convertWord8ToLong(byte[] b) {

        if (b.length!=8) {
            logger.error("Error: Size of byte array to be converted not length 4");
            logger.error(new Integer(b.length).toString());
            System.exit(0);
        }

        ByteBuffer bb = ByteBuffer.wrap(b);
        bb.order(ByteOrder.nativeOrder());

        return (bb.getLong());
    }


    /** Accepts a 4-element byte array and converts to int value based
     * on native byte order (little vs big endian) and returns int value.
     */
    public int convertWord4ToInt(byte[] b) {

        if (b.length!=2 && b.length!=4) {
            logger.error("Error: Size of byte array to be converted not 2 or 4");
            logger.error(new Integer(b.length).toString());
            System.exit(0);
        }

        ByteBuffer bb = ByteBuffer.wrap(b);
        bb.order(ByteOrder.nativeOrder());

        return (bb.getInt());
    }
    
    
    /** Accepts a 4-element byte array and converts to float value based
     * on native byte order (little vs big endian) and returns float value.
     */
    public float convertWord4ToFloat(byte[] b) {

        if (b.length!=4) {
            logger.error("Error: Size of byte array to be converted not length 4");
            logger.error(new Integer(b.length).toString());
            System.exit(0);
        }

        ByteBuffer bb = ByteBuffer.wrap(b);
        bb.order(ByteOrder.nativeOrder());

        return (bb.getFloat());
    }


    /** Accepts a byte array and converts it to a char array.
     */
    public String convertByteArrayToString(byte[] b) {

        ByteBuffer bb = ByteBuffer.wrap(b);
        bb.order(ByteOrder.nativeOrder());
        CharBuffer cb = bb.asCharBuffer();

        return cb.toString();
    }


    /** Checks to see if a specified matrix exists in the data bank.
     *
     * Return values are:
     *    1  valid matrix and it exists
     *    0  valid matrix but does not exist
     *    otherwise, returns an error
     */
    public boolean matrixExists(String matrixName) {

        int  mattype, matnum;
        boolean exists = false;

        mattype = matrixType( matrixName );
        matnum = matrixNumber( matrixName );

        //Check to see if matrix exists by checking flags
        if ((this.matrixFlags[mattype][matnum] & 0x0001) == 1 ) {
            exists = true;
        }
        return exists;
    }


    /** Checks to see if a specified matrix is stored in column-wise format.
     */
    public boolean isColumnWiseMatrix(String matrixName) {

        int  mattype, matnum;
        boolean columnWise = false;

        mattype = matrixType( matrixName );
        matnum = matrixNumber( matrixName );

        //Check to see if matrix is stored in column-wise order by checking flags
        if (mattype==MF && (this.matrixFlags[mattype][matnum] & 0x0002) == 1 ) {
            columnWise = true;
        }
        return columnWise;
    }


    /** Accepts a string such as "mf61" and returns the type of matrix:
    *  MS  1
    *  MO  2
    *  MD  3
    *  MF  4
    */
    public int matrixType (String matrixName) {
        int it=0;

        if (matrixName.length() < 3) {
            logger.error("invalid error type="+matrixName);
            return 0;
        }
        char id = matrixName.charAt(1);

        if      (id=='S'||id=='s') it = 1;
        else if (id=='O'||id=='o') it = 2;
        else if (id=='D'||id=='d') it = 3;
        else if (id=='F'||id=='f') it = 4;
        else {
            logger.error("invalid matrix id="+matrixName);
            return 0;
        }

        return it;
    }


    /** Accepts a string such as "mf61" the matrix number.
    */
    public int matrixNumber (String matrixName) {

        return new Integer(matrixName.substring(2,matrixName.length())).intValue();
    }


    public Emme2FileParameters getFileParameters(int fileNumber) {

        return ifile[fileNumber];
    }


    public int getZonesUsed() {
        return this.zonesUsed;
    }

    public int getMaxZones() {
        return this.maxZones;
    }

    public int getMaxMatrices() {
        return this.global.MMAT;
    }

    public FileChannel getFileChannel() {
        return this.fc;
    }

    public RandomAccessFile getRandomAccessFile() {
        return this.eptr;
    }

    public int[] getInternalZoneNumbers() {
        return this.internCent;
    }

    public int[] getExternalZoneNumbers() {
        return this.externCent;
    }

    public void printMatrixDirectory() {
        logger.debug("");
        logger.debug("Matrix Directory:");
        logger.debug("matrix    name      description");

        for (int m=1; m <= global.MMAT; m++) {
            StringBuffer sb = new StringBuffer(512);

            //Print matrix information if it exists
            if (matrixExists("mf"+m)) {
                sb.append( String.format("mf%02d",  m) );
                logger.debug( sb.toString() );
            }
        }
    }

    public void printRecordTable() {
        logger.debug("");
        logger.debug("Internal Records:");
        logger.debug("file  recs  words/rec  type     offset");

        for (int ifn=1; ifn <= 99; ifn++) {
            StringBuffer sb = new StringBuffer(512);
            sb.append( String.format("%4d",    ifn) );
            sb.append( String.format("%6d",    ifile[ifn].nrecs) );
            sb.append( String.format("%11d",   ifile[ifn].reclen/4) ); //number of words
            sb.append( String.format("%6d",    ifile[ifn].type) );
            sb.append( String.format("%11d",   ifile[ifn].offset) );
            logger.debug( sb.toString() );
        }
    }

}

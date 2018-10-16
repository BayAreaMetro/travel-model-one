package com.pb.common.matrix.util;

import com.pb.common.matrix.*;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.logging.Logger;

/**
 * User: Chris
 * Date: May 24, 2007 - 2:34:06 PM
 */
public class MatrixUtil {

    //protected static Logger logger = Logger.getLogger(MatrixUtil.class);
    protected static Logger logger = Logger.getLogger("MatrixUtil.class");


    //MatrixUtil acts on one or more matrices in an identical manner
    protected Matrix[] matrices;
    private CSVFileReader dataReader = new CSVFileReader();

    public MatrixUtil(Matrix[] matrices) {
        this.matrices = matrices;
    }

    public MatrixUtil(String ... matrixFiles) {
        this(loadMatrices(matrixFiles));
    }

    //name of the matrix is the path to the matrix
    private static Matrix[] loadMatrices(String ... matrixFiles) {
        Matrix[] matrices = new Matrix[matrixFiles.length];
        for (int i = 0; i < matrixFiles.length; i++) {
            matrices[i] = MatrixReader.readMatrix(new File(matrixFiles[i]),matrixFiles[i]);
        }
        return matrices;
    }

    private void writeMatrices(MatrixType type, String ... outputFiles) {
        if (outputFiles.length == 0) {
            logger.severe("No output file specified for writing matrix!");
        }
        if (outputFiles.length == 1 && matrices.length != 1) {
            MatrixWriter.createWriter(type,new File(outputFiles[0])).writeMatrices(null,matrices);
        } else {
            if (matrices.length != outputFiles.length) {
                logger.severe("Number of output files does not match number of matrices!");
            } else {
                for (int i = 0; i < matrices.length; i++) {
                    MatrixWriter.createWriter(type,new File(outputFiles[i])).writeMatrix(matrices[i]);
                }
            }
        }
    }

    private float[] getFilteredNumbersFromColumn(String file, String col, String filterCol, List<String> filterValues, boolean string) {
        TableDataSet data;
        try {
            data = dataReader.readFile(new File(file));
        } catch(IOException e) {
            //I want this to stop here
            logger.severe(e.toString());
            throw new RuntimeException();
        }

        List<Float> numberFilter = new ArrayList<Float>();
        String[] sFilterCol = new String[0];
        float[] fFilterCol = new float[0];
        if (filterCol != null) {
            try {
                if (!string) {
                    for (float f : getArrayFromNumberList(filterValues)) {
                        numberFilter.add(f);
                    }
                    fFilterCol = data.getColumnAsFloat(filterCol);
                } else {
                    sFilterCol = data.getColumnAsString(filterCol);
                }
            } catch (Exception e) {
                logger.severe("Column " + filterCol + " not found in data table:\n\t" + file + "\n\t" + e);
                throw new RuntimeException();
            }
        }

        Set<Float> values = new TreeSet<Float>();
        try {
            int counter = 0;
            for (float f : data.getColumnAsFloat(col)) {
                if (filterCol != null) {
                    if (string && filterValues.contains(sFilterCol[counter])) {
                        values.add(f);
                    } else if (!string && numberFilter.contains(fFilterCol[counter])) {
                        values.add(f);
                    }
                    counter++;
                } else {
                    values.add(f);
                }
            }
        } catch (ArrayIndexOutOfBoundsException e) {
            logger.severe("Column " + col + " not found in data table:\n\t" + file);
            throw new RuntimeException();
        }
        return getArrayFromList(values);
    }

    private float[] getArrayFromNumberList(List<String> numbers) {
        Set<Float> values = new TreeSet<Float>();
        for (String s : numbers) {
            try {
                //split comma-delimited numbers
                for (String n : s.split(",")) {
                    if (n.contains("-")) {
                        //assumes it is of the form XX-XX; treats these as ints and casts to floats
                        String[] nn = n.split("-");
                        for (int i = Integer.valueOf(nn[0]); i <= Integer.valueOf(nn[1]); i++) {
                            values.add((float) i);
                        }
                    } else {
                        values.add(Float.valueOf(n));
                    }
                }
            } catch (IllegalArgumentException e) {
                logger.severe("The following string cannot be parsed into row/column numbers: " + s +
                        "\n\t" + e);
                throw new RuntimeException();
            }
        }
        return getArrayFromList(values);
    }

    //makes a "1-based" array
    private float[] getArrayFromList(Set<Float> list) {
        float[] array = new float[list.size() + 1];
        int counter = 1;
        for (Float i : list)
            array[counter++] = i;
        return array;
    }

    private int[] floatToIntArray(float[] floatArray) {
        int[] intArray = new int[floatArray.length];
        int counter = 0;
        for (float f : floatArray) {
            intArray[counter++] = (int) f;
        }
        return intArray;
    }

    private List<String> getArgumentFromMap(Map<String,List<String>> argMap, String error, int size, String ... args) {
        List<String> argument = getArgumentFromMap(argMap,args);
        if (argument != null) {
            if (argument.size() != size) {
                logger.severe(error);
                argument = null;
            }
        }
        return argument;
    }

    private List<String> getArgumentFromMap(Map<String,List<String>> argMap, String ... args) {
        List<String> argument = null;
        for (String arg : args) {
            if (argMap.containsKey(arg)) {
                argument = argMap.get(arg);
                return argument;
            }
        }
        return argument;
    }

    private int[] getLineOfDataFromArgMap(Map<String,List<String>> argMap, String arg, String callingMethod) {
        List<String> file = getArgumentFromMap(argMap,
                "Only one file may be specified for " + callingMethod + "!",1,arg + SubArg.FILE.string(),SubArg.FILE.string());

        List<String> line;
        String filterCol = null;
        List<String> filterValues = null;
        boolean string = false;

        if (file == null){
            if (argMap.containsKey(SubArg.FILE.string())) {
                return null;
            }
            line = getArgumentFromMap(argMap,arg);
        } else {
            line = getArgumentFromMap(argMap,
                    "Only one " + arg + " argument allowed when specifying a file for " + callingMethod + "!",1,arg);
            //look for filter stuff
            List<String> fc = getArgumentFromMap(argMap,
                    "Only one filter column may be specified for " + callingMethod + "!",1,arg + SubArg.FILTER.string(),SubArg.FILTER.string());
            if (fc != null) {
                filterCol = fc.get(0);
            }
            filterValues = getArgumentFromMap(argMap,arg + SubArg.CLASS.string(),SubArg.CLASS.string());
            if (getArgumentFromMap(argMap,arg + SubArg.STRING.string(),SubArg.STRING.string()) != null) {
                string = true;
            }
            if ((filterCol != null && filterValues == null) || (filterCol == null && filterValues != null)) {
                logger.severe("Must have both filter and class specified if filters are to be used for " + callingMethod + "!");
                return null;
            }
        }

        if (line == null) {
            return null;
        }

        int[] lineData;
        if (file == null) {
            lineData = floatToIntArray(getArrayFromNumberList(line));
        } else {
            lineData = floatToIntArray(getFilteredNumbersFromColumn(file.get(0),line.get(0),filterCol,filterValues,string));
        }

        return lineData;
    }

    private boolean subMatrix(Map<String,List<String>> argMap) {
        int[] columns;
        int[] rows;

        if (argMap.containsKey(SubArg.ROWCOL.string())) {
            columns = getLineOfDataFromArgMap(argMap,SubArg.ROWCOL.string(),"subMatrix");
            rows = columns;
        } else {
            columns = getLineOfDataFromArgMap(argMap,SubArg.COL.string(),"subMatrix");
            rows = getLineOfDataFromArgMap(argMap,SubArg.ROW.string(),"subMatrix");
        }
        if (rows == null && columns == null) {
            logger.severe(SubArg.ROW.string() + " or " + SubArg.COL.string() +
                    " argument must be (validly) specified for subMatrix method!");
            return false;
        }

        int counter = 0;
        for (Matrix m : matrices) {
            if (columns == null)
                columns = m.getExternalColumnNumbers();
            if (rows == null)
                rows = m.getExternalRowNumbers();
            matrices[counter++] = m.getSubMatrix(rows,columns);
        }
        return true;
    }

    private boolean squeezeMatrix(Map<String,List<String>> argMap) {
        List<String> file = getArgumentFromMap(argMap,
                        "Only one alpha/beta file may be specified for squeezeMatrix!",1,SubArg.FILE.string());
        List<String> alpha = getArgumentFromMap(argMap,
                        "Only one alpha column may be specified for squeezeMatrix!",1,SubArg.ALPHA.string());
        List<String> beta = getArgumentFromMap(argMap,
                                "Only one beta column may be specified for squeezeMatrix!",1,SubArg.BETA.string());
        List<String> squeeze = getArgumentFromMap(argMap,
                                "Only one squeeze type may be specified for squeezeMatrix!",1,SubArg.SQUEEZE.string());
        if (file == null || alpha == null || beta == null || squeeze == null) {
            logger.severe("squeezeMatrix method must have file, alpha, beta, and squeeze arguments (validly) specified!");
            return false;
        }

        MatrixCompression.MatrixCompressionType squeezeType;
        try {
            squeezeType = MatrixCompression.MatrixCompressionType.valueOf(squeeze.get(0).toUpperCase());
        } catch (IllegalArgumentException e) {
            logger.severe("Unknown squeeze type: " + squeeze.get(0));
            throw new RuntimeException();
        }

        AlphaToBeta a2b;
        try {
            a2b = new AlphaToBeta(dataReader.readFile(new File(file.get(0))),alpha.get(0),beta.get(0));
        } catch(IOException e) {
            //I want this to stop here
            logger.severe(e.toString());
            throw new RuntimeException();
        }

        MatrixCompression mc = new MatrixCompression(a2b);
        int counter = 0;
        for (Matrix m : matrices) {
            matrices[counter++] = mc.getCompressedMatrix(m,squeezeType);
        }
        return true;
    }

    private enum SubArg {
        ROW("Either the row name from the file which the selected rows will be pulled from\n\t\t" +
                "or a series of row indices specified according to the row/column index rules below"),
        COL("Same as row, only for columns"),
        ROWCOL("Same as row, only for specifying rows and columns together"),
        FILE("The path to the file from which external information (row number, squeeze \n\t\t" +
                "correspondance) will be pulled from"),
        FILTER("A column from file which will be used to filter external information;\n\t\t" +
                "if used, the file and class arguments must all be included"),
        CLASS("Data (numeric (default) or string) which will determine what external information\n\t\t" +
                "to keep if a filter is used (if the data row's filter value is contained\n\t\t" +
                "in these class values, then it will be included in the external information);\n\t\t" +
                "if used, the file and class arguments must also be included"),
        STRING("This argument is used to indicate that the class argument is string (as opposed to numeric)"),
        ALPHA("This argument is used to specify the column name containing the alpha (small) \n\t\tzones in a squeeze procedure"),
        BETA("This argument is used to specify the column name containing the beta (big) \n\t\tzones in a squeeze procedure"),
        SQUEEZE("This argument is used to specify what type of squeeze to perform. Available values are\n\t\t" +
                 Arrays.toString(MatrixCompression.MatrixCompressionType.values()).replaceAll("[\\[\\] ]","").replace(",","\n\t\t"));

        private String description;

        private SubArg(String description) {
            this.description = description;
        }

        private String string() {
            return this.toString().toLowerCase();
        }

        private static String getRowColGenericSet() {
            return "<" + ROW.string() + "/" + COL.string() + "/" + ROWCOL.string() + ">";
        }
    }


    private enum Arg {
        SUBMATRIX("subMatrix","Get a submatrix from each matrix",
                SubArg.ROW.string(),SubArg.COL.string(),SubArg.ROWCOL.string(),
                SubArg.FILE.string(),SubArg.getRowColGenericSet() + SubArg.FILE.string(),
                SubArg.FILTER.string(),SubArg.getRowColGenericSet() + SubArg.FILTER.string(),
                SubArg.CLASS.string(),SubArg.getRowColGenericSet() + SubArg.CLASS.string(),
                SubArg.STRING.string()) {
            boolean runMethod(MatrixUtil mu, Map<String,List<String>> argMap) {
                return mu.subMatrix(argMap);
            }
        },
        SQUEEZEMATRIX("squeezeMatrix","Squeeze a matrix to a smaller one",
                SubArg.FILE.string(),SubArg.ALPHA.string(),SubArg.BETA.string(),SubArg.SQUEEZE.string()) {
            boolean runMethod(MatrixUtil mu, Map<String,List<String>> argMap) {
                return mu.squeezeMatrix(argMap);
            }
        };

        abstract boolean runMethod(MatrixUtil mu, Map<String,List<String>> argMap);

        private String description;
        private String name;
        private String[] args;

        private Arg(String methodName, String description, String ... args) {
            this.name = methodName;
            this.description = description;
            this.args = args;
        }
    }

    private static class NestedCommandLine {

        List<String> mainArgs = new ArrayList<String>();
        List<Map<String,List<String>>> argTree = new ArrayList<Map<String,List<String>>>();

        NestedCommandLine(String[] args) {
            processArgs(args);
        }

        //this thing skips until it hits a double dash!
        private void processArgs(String[] args) {
            boolean foundFirst = false;
            String lastArg = null;
            for (String s : args) {

                //keep going till we get to a main argument
                if (!foundFirst) {
                    if (!s.substring(0,2).equals("--")) {
                        continue;
                    }
                    foundFirst = true;
                }

                if (s.length() > 1 && s.substring(0,2).equals("--")) {
                    mainArgs.add(s.substring(2));
                    argTree.add(new LinkedHashMap<String,List<String>>());
                    argTree.get(argTree.size() - 1).put("",new ArrayList<String>());
                    lastArg = "";
                } else if (s.length() > 0 && s.substring(0,1).equals("-")) {
                    lastArg = s.substring(1).toLowerCase();
                    argTree.get(argTree.size() - 1).put(lastArg,new ArrayList<String>());
                } else {
                    argTree.get(argTree.size() - 1).get(lastArg).add(s);
                }
            }
        }
    }

    private static void usage() {
        StringBuffer usage = new StringBuffer("\n");
        usage.append("MatrixUtil - A class allowing nested matrix operations.\n\n");
        usage.append("usage: java MatrixUtil --mat <matrix file 1> <matrix file 2> ...\n\t");
        usage.append("--out <output file 1> <output file 2> ...\n\t");
        usage.append("[--type <output matrix type>]\n\t");
        usage.append("[--<matrix method 1> \n\t\t");
        usage.append("-<method 1 arg 1> <arg 1 sub-arg 1> <arg 1 sub-arg 2> ...\n\t\t");
        usage.append("-<method 1 arg 2> <arg 2 sub-arg 1> <arg 2 sub-arg 2> ...\n\t\t");
        usage.append("...]\n\t");
        usage.append("[--<matrix method 2> \n\t\t");
        usage.append("-<method 2 arg 1> <arg 1 sub-arg 1> <arg 1 sub-arg 2> ...\n\t\t");
        usage.append("-<method 2 arg 2> <arg 2 sub-arg 1> <arg 2 sub-arg 2> ...\n\t\t");
        usage.append("...]\n\t");
        usage.append("[...]\n");
        usage.append("\nThe output matrix type defaults to CSV, but can be specified as:\n");
        for (MatrixType type : MatrixType.values()) {
            usage.append("\t").append(type.toString().toLowerCase()).append("\n");
        }
        usage.append("\nIf multiple input matrices are specified, but only one output file is,");
        usage.append("then the program will attempt to write the matrices into a single file format.");
        usage.append("\nNote that many of the matrix formats do not support such a format.\n");
        usage.append("\n<matrix method X> can be any of the following:\n");
        for (Arg arg : Arg.values()) {
            usage.append("\n\t").append(arg.name).append(" - ").append(arg.description).append("\n\t\tavailable args: ");
            for (String subArg : arg.args) {
                usage.append("-").append(subArg).append(" ");
            }
            usage.append("\n");
        }
        usage.append("\nwhere the arguments are defined as:\n");
        for (SubArg subArg : SubArg.values()) {
            usage.append("\n\t").append(subArg.string()).append(" - ").append(subArg.description);
            usage.append("\n");
        }
        usage.append("\n").append(SubArg.getRowColGenericSet()).append(" indicates that a row/col/rowcol specific argument can be specified (e.g. -rowfile)\n");
        usage.append("\nThe index specification (for row/col/rowcol) can be a list of space/comma delimited integers,\n")
                .append("or a range in the form of X-Y, where X < Y, an example is:\n\n\t")
                .append("1 2 5,9,3,10-13 15-17\n\nwhich is equivalent to\n\n\t")
                .append("1 2 3 5 9 10 11 12 13 15 16 17\n");
        logger.info(usage.toString());
    }

    public static void main(String[] args) {

        if (args.length == 0 || args[0].replace("-","").toLowerCase().equals("help")) {
            usage();
            return;
        }

        NestedCommandLine cmdLine = new NestedCommandLine(args);

        MatrixUtil mu;
        String[] matrixFiles;
        String[] outputFiles;
        MatrixType type = MatrixType.CSV;

        //get input matrix file(s)
        int index = cmdLine.mainArgs.indexOf("mat");
        if (index > -1) {
            cmdLine.mainArgs.remove(index);
            List<String> mf = cmdLine.argTree.remove(index).get("");
            matrixFiles = mf.toArray(new String[mf.size()]);
        } else {
            logger.severe("No matrices specified!");
            usage();
            return;
        }

        //get output file(s)
        index = cmdLine.mainArgs.indexOf("out");
        if (index > -1) {
            cmdLine.mainArgs.remove(index);
            List<String> mf = cmdLine.argTree.remove(index).get("");
            outputFiles = mf.toArray(new String[mf.size()]);
        } else {
            logger.severe("No output files specified!");
            usage();
            return;
        }

        //get (optional) type
        index = cmdLine.mainArgs.indexOf("type");
        if (index > -1) {
            cmdLine.mainArgs.remove(index);
            type = MatrixType.lookUpMatrixType(
                    cmdLine.argTree.remove(index).get("").get(0));
        }

        //Load up matrices
        //check to make sure they are all files
        boolean filesOk = true;
        for (String f : matrixFiles) {
            if (!(new File(f)).exists()) {
                logger.severe("Matrix file does not exist!:\n\t" + f);
                filesOk = false;
            }
            if (!filesOk)
                return;
        }
        mu = new MatrixUtil(matrixFiles);

        //Get output file name(s) and check them
        //This at once checks to see if the output file string is a file (not a directory),
        //  whether it exists or not, and whether is can be created/written to
        for (String f : outputFiles) {
            try {
                if (!(new File(f)).createNewFile()) {
                    logger.warning("Matrix file exists!\n\t" + f);
                } else {
                    (new File(f)).delete();
                }
            } catch (IOException e) {
                e.printStackTrace();
                return;
            }
        }

        //Cycle through all of the args and do what is asked for, in that order
        int counter = 0;
        for (String arg : cmdLine.mainArgs) {
            try {
                if (!Arg.valueOf(arg.toUpperCase()).runMethod(mu,cmdLine.argTree.get(counter++))) {
                    logger.severe("Error in execution; will not finish. Matrices will not be saved.");
                    return;
                }
            } catch (IllegalArgumentException e) {
                if (arg.equalsIgnoreCase("mat") || arg.equalsIgnoreCase("out") || arg.equalsIgnoreCase("type"))
                    logger.severe("Only one main argument '" + arg + "' allowed!");
                else
                    logger.severe("No main argument " + arg + " allowed!");
                return;
            }
        }

        //write out matrices
        mu.writeMatrices(type,outputFiles);

    }




}

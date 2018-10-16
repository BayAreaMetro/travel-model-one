package com.pb.models.synpop;

import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.*;

/**
 * The {@code SpgAcsData} ...
 *
 * @author crf <br/>
 *         Started Apr 4, 2011 4:27:09 PM
 */
public class SpgAcsData {
    protected static Logger logger = Logger.getLogger(SpgAcsData.class);

    private static String[] getAcsDataFromList(String line) {
        return line.split(","); //should work for now
    }

    private static int[] getAttributeIndex(List<String> header, List<String> attributes, String source) {
        int[] attributeIndex = new int[attributes.size()];
        int counter = 0;
        for (String attribute : attributes) {
            int attIndex = header.indexOf(attribute);
            if (attIndex == -1)
                throw new RuntimeException(String.format("Attribute '%s' not found in %s",attribute,source));
            attributeIndex[counter++] = attIndex;
        }
        return attributeIndex;
    }

    private static AcsDataTransfer[] getTransfers(List<String> attributes, Map<String,AcsDataTransfer> transfers) {
        AcsDataTransfer[] fullTransfers = new AcsDataTransfer[attributes.size()];
        int counter = 0;
        for (String attribute : attributes)
            fullTransfers[counter++] = transfers.containsKey(attribute) ? transfers.get(attribute) : ZEROING_DATA_TRANSFER;
        return fullTransfers;
    }

    //TableDataSet hhTable, TableDataSet personTable, HashMap fieldMap, String year, SwIndustry ind, SwOccupation occ, Workers hhWorkers
    public static TableDataSet readAcsData(String acsFile, List<String> numericAttributes, List<String> stringAttributes,
                                           List<AcsFilter> filters, Map<String,AcsDataTransfer> dataTransfers) {
        List<List<String>> numericData = new LinkedList<List<String>>();
        for (String attribute : numericAttributes)
            numericData.add(new LinkedList<String>());
        List<List<String>> stringData = new LinkedList<List<String>>();
        for (String attribute : stringAttributes)
            stringData.add(new LinkedList<String>());
        
        BufferedReader acsReader = null;
        try {
            acsReader = new BufferedReader(new FileReader(acsFile));

            List<String> header = Arrays.asList(getAcsDataFromList(acsReader.readLine()));
            int[] numericAttributeIndex = getAttributeIndex(header,numericAttributes,acsFile);
            int[] stringAttributeIndex = getAttributeIndex(header,stringAttributes,acsFile);
            AcsDataTransfer[] numericTransfers = getTransfers(numericAttributes,dataTransfers);
            AcsDataTransfer[] stringTransfers = getTransfers(stringAttributes,dataTransfers);
            List<String> filterAtts = new LinkedList<String>();
            for (AcsFilter filter : filters)
                filterAtts.add(filter.getField());
            int[] filterIndex = getAttributeIndex(header,filterAtts,acsFile);

            String line;
            lineLoop : while ((line = acsReader.readLine()) != null) {
                String[] data = getAcsDataFromList(line);

                //skip filtered data
                int counter = 0;
                for (AcsFilter filter : filters)
                    if (!filter.pass(data[filterIndex[counter++]]))
                        continue lineLoop;

                counter = 0;
                for (List<String> col : numericData) {
                    col.add(numericTransfers[counter].getData(data[numericAttributeIndex[counter]]));
                    counter++;
                }
                counter = 0;
                for (List<String> col : stringData) {
                    col.add(stringTransfers[counter].getData(data[stringAttributeIndex[counter]]));
                    counter++;
                }
            }
        } catch (IOException e) {
            logger.fatal("Error reading ACS data from " + acsFile,e);
            throw new RuntimeException(e);
        } catch (RuntimeException e) {
            logger.fatal("Error reading ACS data from " + acsFile,e);
            throw new RuntimeException(e);
        } finally {
            if (acsReader != null)
                try {
                    acsReader.close();
                } catch (IOException e) {
                    //suppress
                }
        }
        
        //now build table data sets and merge
        //though they'll be ints, we need float array for table data set
        int numericCount = numericData.size();                                                                                    
        TableDataSet numericDataSet = null;
        if (numericCount > 0) {               
            float[][] nData = new float[numericData.get(0).size()][numericCount]; //if zero, then empty initial
            int outerCounter = 0;
            for (List<String> column : numericData) {
                int innerCounter = 0;
                for (String data : column) {
                    try {
                        nData[innerCounter++][outerCounter] = data.length() == 0 ? 0 : Integer.parseInt(data); //cast it to an int, and then have it promoted by Java to a float
                    } catch (NumberFormatException e) {
                        logger.error("Number format exception for column " + numericAttributes.get(outerCounter) + " = " + data);
                        throw e;
                    }
                }
                outerCounter++;
            }
            numericDataSet = TableDataSet.create(nData,numericAttributes.toArray(new String[numericAttributes.size()]));
        }                                                               
        int stringCount = stringData.size();                                                                                    
        TableDataSet stringDataSet = null;
        if (stringCount > 0) {               
            String[][] sData = new String[stringData.get(0).size()][stringCount]; //if zero, then empty initial
            int outerCounter = 0;
            for (List<String> column : stringData) {
                int innerCounter = 0;
                for (String data : column)
                    sData[innerCounter++][outerCounter] = data; //cast it to an int, and then have it promoted by Java to a float
                outerCounter++;
            }
            stringDataSet = TableDataSet.create(sData,stringAttributes.toArray(new String[stringAttributes.size()]));
        }
        if (numericDataSet == null) {
            return stringDataSet;
        } else if (stringDataSet == null) {
            return numericDataSet;
        } else {
            numericDataSet.merge(stringDataSet);
            return numericDataSet;
        }
    }

    public static interface AcsDataTransfer {
        String getData(String inData);
    }

    public static final AcsDataTransfer PASSING_DATA_TRANSFER = new AcsDataTransfer() {
            public String getData(String inData) {
                return inData;
            }
        };

    public static final AcsDataTransfer ZEROING_DATA_TRANSFER = new AcsDataTransfer() {
        public String getData(String inData) {
            return inData.length() == 0 ? "0" : inData;
        }
    };

    public static interface AcsFilter {
        String getField();
        boolean pass(String value);
    }
    
    public static AcsFilter getBlockingFilter(final String acsField, List<String> blockingValues) {
        return getSimpleFilter(acsField,blockingValues,true);
    }                                                        
    
    public static AcsFilter getPassingFilter(final String acsField, List<String> passingValues) {
        return getSimpleFilter(acsField,passingValues,false);
    }

    private static AcsFilter getSimpleFilter(final String acsField, List<String> values, final boolean blocking) {
        final Set<String> vals = new HashSet<String>(values);
        return new AcsFilter() {
            public String getField() {
                return acsField;
            }

            public boolean pass(String value) {
                if (vals.contains(value))
                    return !blocking;
                return blocking;
            }
        };
    }

    public static AcsFilter getBlockingIntFilter(final String acsField, int[] blockingValues) {
        return getSimpleIntFilter(acsField,blockingValues,true);
    }

    public static AcsFilter getPassingIntFilter(final String acsField, int[] passingValues) {
        return getSimpleIntFilter(acsField,passingValues,false);
    }

    private static AcsFilter getSimpleIntFilter(final String acsField, int[] values, final boolean blocking) {
        final Set<Integer> vals = new HashSet<Integer>();
        for (int val : values)
            vals.add(val);
        return new AcsFilter() {
            public String getField() {
                return acsField;
            }

            public boolean pass(String value) {
                if (vals.contains(Integer.parseInt(value)))
                    return !blocking;
                return blocking;
            }
        };
    }

    //all static stuff above is unstateful, and stuff below is a little more implementation specific

    public AcsDataTransfer getHHUnitsDataTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("bb") || inData.length() == 0  ? "0" : inData;
            }
        };
    }

    public AcsDataTransfer getHHIncDataTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("bbbbbbbb") || inData.length() == 0  ? "0" : inData;
            }
        };
    }

    public AcsDataTransfer getHHVehDataTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                if (inData.length() == 0)
                    return "0";
                switch (inData.charAt(0)) {
                    case 'b' : return "0";
                    case '0' : return "1";
                    case '1' : return "2";
                    case '2' : return "3";
                    case '3' : return "4";
                    case '4' : return "5";
                    case '5' : return "6";
                    case '6' : return "8"; //skipping 6 here - need to check on this: todo
                }
                return inData.equals("b") ? "0" : inData;
            }
        };
    }

    public AcsDataTransfer getPersonIndOccDataTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("bbbb") || inData.length() == 0  ? "0" : inData;
            }
        };
    }

    public AcsDataTransfer getPersonLaborTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("b") || inData.length() == 0  ? "0" : inData;
            }
        };
    }

    public AcsDataTransfer getPersonSexTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("1") ? "0" : "1";
            }
        };
    }

    public AcsDataTransfer getPersonSchoolTransfer() {
        return new AcsDataTransfer() {
            public String getData(String inData) {
                return inData.equals("b") || inData.length() == 0 ? "0" : inData;
            }
        };
    }
}

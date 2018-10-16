/*
 * Copyright 2006 PB Consult Inc.
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
package com.pb.models.reference;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.TextFile;
import com.pb.common.util.ResourceUtil;
import com.pb.common.util.SeededRandom;

import java.io.File;
import java.io.IOException;
import java.util.*;

/**
 * This class is used for holding the
 * list of industries, occupation and split
 * industried that are defined for this project
 *
 * This class basically encapsulates the
 * "IndustryOccupationSplitIndustryCorrespondence.csv" file
 * that must be created for any project using
 * SPG code.
 * Author: Christi Willison
 * Date: Oct 12, 2006
 * Email: willison@pbworld.com
 * Created by IntelliJ IDEA.
 */


public class IndustryOccupationSplitIndustryReference {

    TableDataSet correspondenceFile;
    Set<String> industryLabels;    //these can be returned to the user if
    Set<String> occupationLabels;  //a unique set of labels is needed.
    Set<String> splitIndustryLabels;

    int maxIndustryIndex;
    int maxOccupationIndex;
    int maxSplitIndustryIndex;

    String[] industryLabelsByIndex;
    String[] occupationLabelsByIndex;
    String[] splitIndustryLabelsByIndex;

    boolean blnNoPortion;

    //Random mrndGenerator;

    HashMap<String,Integer> industryLabelsToIndex;       //used for lookup only
    HashMap<String,Integer> occupationLabelsToIndex;     //no public accessors.
    HashMap<String,Integer> splitIndustryLabelsToIndex;

    //int[][] industryOccupationToSplit;
    float[] PortionValues = {1.0f, 2.0f, 3.0f};
    /*
    hshIndustryOccupationToSplit maps a string to another HashMap
    The string will be IndustryIndex.tostring + _ + OccupationIndex.toString
    The internal HashMap maps an Integer (SplitIndustryIndex) to the Portion percentage Float.
     */
    HashMap<String, HashMap<Integer, Float>> hshIndustryOccupationToSplit;

    enum Type {Industry, Occupation, SplitIndustry, } // these correspond to header names in corresp. file

    public IndustryOccupationSplitIndustryReference(String corresFile){
        //mrndGenerator = new Random();
        readCorrespondenceFile(corresFile);

        blnNoPortion = correspondenceFile.getColumnCount() == 6;

        maxIndustryIndex = findMaxIndex(Type.Industry);
        maxOccupationIndex = findMaxIndex(Type.Occupation);
        maxSplitIndustryIndex = findMaxIndex(Type.SplitIndustry);

        industryLabels = defineLabels(Type.Industry, industryLabels);
        occupationLabels = defineLabels(Type.Occupation, occupationLabels);
        splitIndustryLabels = defineLabels(Type.SplitIndustry, splitIndustryLabels);

        industryLabelsToIndex = defineLabelToIndexCorrespondence(Type.Industry, industryLabelsToIndex );
        occupationLabelsToIndex = defineLabelToIndexCorrespondence(Type.Occupation, occupationLabelsToIndex);
        splitIndustryLabelsToIndex = defineLabelToIndexCorrespondence(Type.SplitIndustry, splitIndustryLabelsToIndex);

        industryLabelsByIndex = createLabelArray(Type.Industry, industryLabelsByIndex);
        occupationLabelsByIndex = createLabelArray(Type.Occupation, occupationLabelsByIndex);
        splitIndustryLabelsByIndex = createLabelArray(Type.SplitIndustry, splitIndustryLabelsByIndex);

        //industryOccupationToSplit = defineIndustryOccupationSplitCorrespondence(industryOccupationToSplit);
        hshIndustryOccupationToSplit = definehshIndustryOccupationSplitCorrespondence();
    }


    private void readCorrespondenceFile(String file){

        CSVFileReader reader = new CSVFileReader();
        try {
            correspondenceFile = reader.readFile(new File(file));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private Set<String> defineLabels(Type labelCol, Set<String> uniqueValues){
        String[] colStringValues = correspondenceFile.getColumnAsString(labelCol.toString());

        uniqueValues = new HashSet<String>();
        for(String colStringValue: colStringValues){
            uniqueValues.add(colStringValue);
        }

        return uniqueValues;
    }

    private HashMap<String, Integer> defineLabelToIndexCorrespondence(Type labelCol, HashMap<String, Integer> labelToIndex){
        String[] colStringValues = correspondenceFile.getColumnAsString(labelCol.toString());
        int[] colIntValues = correspondenceFile.getColumnAsInt(labelCol.toString() + "Index");

        labelToIndex = new HashMap<String, Integer>();
        String label;
        Integer index;
        for(int i=0; i< colStringValues.length; i++){
            label = colStringValues[i];
            index = colIntValues[i];
            labelToIndex.put(label, index);
        }

        return labelToIndex;
    }

    private String[] createLabelArray(Type category, String[] labelArray){
        int length;
        HashMap<String, Integer> map = null;
        switch(category){
            case Industry:
                length = industryLabels.size();
                if(length == maxIndustryIndex + 1 ) //indicates that the index starts at 0
                    labelArray = new String[length];
                else
                    labelArray = new String[length+1]; //index starts at 1
                map = industryLabelsToIndex;
                break;
            case Occupation:
                length = occupationLabels.size();
                if(length == maxOccupationIndex + 1)
                    labelArray = new String[length];
                else
                    labelArray = new String[length + 1];
                map = occupationLabelsToIndex;
                break;
            case SplitIndustry:
                length = splitIndustryLabels.size();
                if(length == maxSplitIndustryIndex + 1)
                    labelArray = new String[length];
                else
                    labelArray = new String[length + 1];
                map = splitIndustryLabelsToIndex;
                break;
        }

        for (String s : map.keySet()) {
            int index = map.get(s);
            labelArray[index] = s;
        }
        return labelArray;
    }

   private HashMap<String, HashMap<Integer, Float>> definehshIndustryOccupationSplitCorrespondence(){
        int intIndustryIndex;
        int intOccupationIndex;
        int intSplitIndex;
        float fltPortion;
        float[] PortionValues;

        String strMap;
        HashMap<Integer, Float> hshTemp;
        HashMap<String, HashMap<Integer, Float>> hshCorrespondence = new HashMap<String, HashMap<Integer, Float>>();
        int[] industryIndexValues = correspondenceFile.getColumnAsInt(Type.Industry.toString() + "Index");
        int[] occupationIndexValues = correspondenceFile.getColumnAsInt(Type.Occupation.toString() + "Index");
        int[] splitIndexValues = correspondenceFile.getColumnAsInt(Type.SplitIndustry.toString() + "Index");
        if (!blnNoPortion) {
            PortionValues = correspondenceFile.getColumnAsFloat("Portion");
        } else {
            PortionValues = new float[industryIndexValues.length];
            Arrays.fill(PortionValues, 1.0f);
        }

        for(int i=0; i< industryIndexValues.length; i++){

            intIndustryIndex = industryIndexValues[i];
            intOccupationIndex = occupationIndexValues[i];
            intSplitIndex = splitIndexValues[i];
            fltPortion = PortionValues[i];

            strMap = intIndustryIndex + "_" + intOccupationIndex;

            if (hshCorrespondence.containsKey(strMap)) {
                hshTemp = hshCorrespondence.get(strMap);
                hshTemp.put(intSplitIndex, fltPortion);
                hshCorrespondence.put(strMap, hshTemp);
            } else {
                hshTemp = new HashMap<Integer, Float>();
                hshTemp.put(intSplitIndex, fltPortion);
                hshCorrespondence.put(strMap, hshTemp);
            }
        }
        return hshCorrespondence;

    }

    public int getSplitIndustryIndex(int IndustryIndex, int OccupationIndex) {

        double fltSelector = SeededRandom.getRandom();
        int intSplitIndustryIndex = 0;
        float fltTotal = 0.0f;
        float fltCurrent;
        HashMap<Integer, Float> hshSplitIndustry;
        Iterator<Integer> itrSplitIndustry;
        String strIndustryOccupation = IndustryIndex + "_" + OccupationIndex;
        if (hshIndustryOccupationToSplit.containsKey(strIndustryOccupation)) {
            hshSplitIndustry = hshIndustryOccupationToSplit.get(strIndustryOccupation);
            Set<Integer> setIndex = hshSplitIndustry.keySet();
            itrSplitIndustry = setIndex.iterator();
            while(itrSplitIndustry.hasNext()) {
                intSplitIndustryIndex = itrSplitIndustry.next();
                fltCurrent = hshSplitIndustry.get(intSplitIndustryIndex);
                fltTotal += fltCurrent;
                if (fltSelector < fltTotal) {
                    break;
                }
            }

        } else {
           throw new RuntimeException("Industry: " + IndustryIndex + "and Occupation: " + OccupationIndex + "are not a valid combination.");
        }

        return intSplitIndustryIndex;
    }

    private int findMaxIndex (Type category){
        int[] indices = new int[0];
        int max = 0;
        switch(category){
            case Industry:
                indices = correspondenceFile.getColumnAsInt(Type.Industry.toString() + "Index");
                break;
            case Occupation:
                indices = correspondenceFile.getColumnAsInt(Type.Occupation.toString() + "Index");
                break;
            case SplitIndustry:
                indices = correspondenceFile.getColumnAsInt(Type.SplitIndustry.toString() + "Index");
                break;
        }
        for(int i: indices){
            if(i > max)
                max = i;
        }
        return max;
    }

    private int getIndexFromLabel(Type category, String label){
        try {
            switch(category){
                case Industry:
                    return industryLabelsToIndex.get(label);
                case Occupation:
                    return occupationLabelsToIndex.get(label);
                case SplitIndustry:
                    return splitIndustryLabelsToIndex.get(label);
                default:
                    return -1;  //should never get here
            }
         } catch (Exception e) {
            throw new RuntimeException(label + " is not a valid " + category);
        }
    }

    private String getLabelFromIndex(Type category, int index){
        try {
            switch(category){
                case Industry:
                    return industryLabelsByIndex[index];
                case Occupation:
                    return occupationLabelsByIndex[index];
                case SplitIndustry:
                    return splitIndustryLabelsByIndex[index];
                default:
                    return "";  //should never get here
            }
         } catch (Exception e) {
            throw new RuntimeException(index + " is not a valid index number in " + category);
        }
    }

    private Set<String> getLabels(Type category){
        switch(category){
            case Industry: return industryLabels;
            case Occupation: return occupationLabels;
            case SplitIndustry: return splitIndustryLabels;
            default: return null; //should never get here
        }
    }


    public int getIndustryIndexFromLabel(String label){
        return getIndexFromLabel(Type.Industry, label);
    }

    public int getOccupationIndexFromLabel(String label){
        return getIndexFromLabel(Type.Occupation, label);
    }

    public int getSplitIndustryIndexFromLabel(String label){
        return getIndexFromLabel(Type.SplitIndustry, label);
    }

    public String getIndustryLabelFromIndex(int index){
        return getLabelFromIndex(Type.Industry, index);
    }

    public String getOccupationLabelFromIndex(int index){
        return getLabelFromIndex(Type.Occupation, index);
    }

    public String getSplitIndustryLabelFromIndex(int index){
        return getLabelFromIndex(Type.SplitIndustry, index);
    }

    public int getNumOfIndustries(){
        return industryLabels.size();
    }

    public int getNumOfOccupations(){
        return occupationLabels.size();
    }

    public int getNumOfSplitIndustries(){
        return splitIndustryLabels.size();
    }

    public Set<String> getIndustryLabels(){
        return getLabels(Type.Industry);
    }

    public Set<String> getOccupationLabels(){
        return getLabels(Type.Occupation);
    }

    public Set<String> getSplitIndustryLabels(){
        return getLabels(Type.SplitIndustry);
    }

    public String[] getIndustryLabelsByIndex(){
        return industryLabelsByIndex;
    }

    public String[] getOccupationLabelsByIndex(){
        return occupationLabelsByIndex;
    }

    public String[] getSplitIndustryLabelsByIndex(){
        return splitIndustryLabelsByIndex;
    }

    public int getMaxIndustryIndex(){
        return maxIndustryIndex;
    }

    public int getMaxOccupationIndex(){
        return maxOccupationIndex;
    }

    public int getMaxSplitIndustryIndex(){
        return maxSplitIndustryIndex;
    }

    public HashMap<String, Integer> getIndustryLabelToIndexMapping(){
        return industryLabelsToIndex;
    }

    public HashMap<String, Integer> getOccupationLabelToIndexMapping(){
        return occupationLabelsToIndex;
    }

    public boolean isIndustryLabelValid(String label){
        return industryLabels.contains(label);
    }

    public boolean isSplitIndustryLabelValid(String label){
        return splitIndustryLabels.contains(label);
    }

    public boolean isOccupationLabelValid(String label){
        return occupationLabels.contains(label);
    }

    /////the following code is for creating a dummy file to allow the old code to be leveraged, though we're dropping the need for this correspondence
    public static final String INDUSTRY_OCCUPATION_SPLIT_CORRESPONDENCE_FILE_PROPERTY = "industry.occupation.to.split.industry.correspondence";
    public static final String INDUSTRY_LIST_FILE_PROPERTY = "industry.list.file";
    public static final String OCCUPATION_LIST_FILE_PROPERTY = "occupation.list.file";

    //these next two methods act as such: if the split correspondence file is missing, then it is assumed that it is
    // not necessary and a dummy correspondence file is built
    public static String getSplitCorrespondenceFilepath(ResourceBundle rb) {
        return getSplitCorrespondenceFilepath(ResourceUtil.changeResourceBundleIntoHashMap(rb));
    }

    public static String getSplitCorrespondenceFilepath(Map rb) {
        String filepath = (String) rb.get(INDUSTRY_OCCUPATION_SPLIT_CORRESPONDENCE_FILE_PROPERTY);
        checkForSplitCorrespondence(filepath,rb);
        return filepath;
    }

    //builds dummy correspondence if it doesn't currently exist
    private static void checkForSplitCorrespondence(String filepath, Map rb) {
        File corrFile = new File(filepath);
        if (!corrFile.exists())
            buildDummyCorrespondenceFile(filepath,rb);
    }

    private static void buildDummyCorrespondenceFile(String filepath, Map rb) {
            //assume that we can build a dummy
        TableDataSet industryList;
        TableDataSet occupationList;
        CSVFileReader reader = new CSVFileReader();
        try {
            industryList = reader.readFile(new File((String) rb.get(INDUSTRY_LIST_FILE_PROPERTY)));
            occupationList = reader.readFile(new File((String) rb.get(OCCUPATION_LIST_FILE_PROPERTY)));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        //both files assumed to be id,name
        Map<Integer,String> industries = new TreeMap<Integer,String>();
        Map<Integer,String> occupations = new TreeMap<Integer,String>();
        for (int i = 1; i <= industryList.getRowCount(); i++)
            industries.put((int) industryList.getValueAt(i,1),industryList.getStringValueAt(i,2));
        for (int i = 1; i <= occupationList.getRowCount(); i++)
            occupations.put((int) occupationList.getValueAt(i,1),occupationList.getStringValueAt(i,2));

        //no need to build tds, instead just build the file out by hand
        //expecting Industry,IndustryIndex,Occupation,OccupationIndex,SplitIndustry,SplitIndustryIndex,Portion
        TextFile tf = new TextFile();
        tf.add("Industry,IndustryIndex,Occupation,OccupationIndex,SplitIndustry,SplitIndustryIndex,Portion");
        for (int i : industries.keySet())
            for (int j : occupations.keySet())
                tf.add(industries.get(i) + "," +
                       i + "," +
                       occupations.get(j) + "," +
                       j + "," +
                       industries.get(i) + "," +
                       i + ",1.0");
        tf.writeTo(filepath);
    }





    public static void main(String[] args) {
        //String file = "/models/IndustryOccupationSplitIndustryCorrespondenceTLUMIP.csv";
        String file = "/models/IndustryOccupationSplitIndustryCorrespondenceTLUMIP.csv";
        IndustryOccupationSplitIndustryReference ref = new IndustryOccupationSplitIndustryReference(file);

        System.out.println("Number of unique Industries: " + ref.getNumOfIndustries());
        System.out.println("Number of unique Occupations: " + ref.getNumOfOccupations());
        System.out.println("Number of unique SplitIndustries: " + ref.getNumOfSplitIndustries());

        System.out.println("Max Industry Index: " + ref.getMaxIndustryIndex());
        System.out.println("Max Occupation Index: " + ref.getMaxOccupationIndex());
        System.out.println("Max SplitIndustry Index: " + ref.getMaxSplitIndustryIndex());

        System.out.println("Ag fish (1): " + ref.getIndustryIndexFromLabel("Agriculture Forestry and Fisheries"));
        System.out.println("Tran Handling (11): " + ref.getIndustryIndexFromLabel("Transportation Handling"));

        System.out.println("Main worker (15): " + ref.getOccupationIndexFromLabel("Maintenance and repair workers"));
        System.out.println("Ag worker (13): " + ref.getOccupationIndexFromLabel("Agriculture workers"));

        System.out.println("Wholesale Prod (11): " + ref.getSplitIndustryIndexFromLabel("Wholesale Production"));
        System.out.println("Post-sec (22): " + ref.getSplitIndustryIndexFromLabel("Post-Secondary Education"));

        System.out.println("Industry 0 (NoIndustry)" + ref.getIndustryLabelFromIndex(0));
        System.out.println("Industry 16 (GovAndOther)" + ref.getIndustryLabelFromIndex(16));

        System.out.println("Occupation 0 (NoOccupation)" + ref.getOccupationLabelFromIndex(0));
        System.out.println("Occupation 9 (FoodWrk)" + ref.getOccupationLabelFromIndex(9));

        System.out.println("SplitIndustry 4 (Metal Office)" + ref.getSplitIndustryLabelFromIndex(4));
        System.out.println("SplitIndustry 15 (Hotel)" + ref.getSplitIndustryLabelFromIndex(15));

        System.out.println("SplitIndustryIndex for AgFish - ServiceWrkrs (1)" + ref.getSplitIndustryIndex(1,8));
        System.out.println("SplitIndustryIndex for Util/Profs (19)" + ref.getSplitIndustryIndex(12,3));


    }
}


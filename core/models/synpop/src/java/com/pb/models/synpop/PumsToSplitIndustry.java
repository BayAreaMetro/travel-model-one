package com.pb.models.synpop;

import com.pb.common.util.ResourceUtil;
import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.*;

/**
 * The {@code PumsToSplitIndustry} builds a connection between pums industry and occupations and the pecas split industries.
 * This is similar to IndustryOccupationSplitIndustry, but it used to select a specific split industry (based on a randomized
 * choice) rather than proportioning aggregates. That is, a split industry can be selected when the pums data is read in,
 * rather than post processing to construct their splits.
 *
 * @author crf <br/>
 *         Started May 23, 2011 10:14:30 AM
 */
public class PumsToSplitIndustry {
    public static final String PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY = "pums.to.split.industry.file";

    private final Map<Integer,String> splitIndustryIdToName; //for convenience
    private final Map<Integer,Map<Integer,IndustryOccupationSplit>> industryOccupationSplits; //pums ind id -> pums occ id -> split object
    private final Random random;

    public PumsToSplitIndustry(Map rb) {
        splitIndustryIdToName = new HashMap<Integer, String>();
        industryOccupationSplits = new HashMap<Integer,Map<Integer,IndustryOccupationSplit>>();
        loadDataFromFile((String) rb.get(PUMS_TO_SPLIT_INDUSTRY_FILE_PROPERTY));
        random = new Random(Integer.parseInt((String) rb.get("randomSeed")));
        for (int i : industryOccupationSplits.keySet())
            for (int o : industryOccupationSplits.get(i).keySet())
                industryOccupationSplits.get(i).get(o).buildProportionSplits();
    }

    private void loadDataFromFile(String pumsToSplitIndustryFile) {
        //file format:
        //pums_industry_code ,pums_occ_code,split_industry_id,split_industry,proportion

        //no reason to load into table data set, so just read and parse line by line
        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new FileReader(pumsToSplitIndustryFile));
            String line;
            boolean first = true;
            while ((line = reader.readLine()) != null) {
                if (first) { //skip header
                    first = false;
                    continue;
                }
                String[] data = line.split(",");
                int pumsIndustryId = Integer.parseInt(data[0].trim());
                int pumsOccupationId = Integer.parseInt(data[1].trim());
                int splitIndustryId = Integer.parseInt(data[2].trim());
                String splitIndustry = data[3].trim();
                double proportion = Double.parseDouble(data[4]);

                if (!splitIndustryIdToName.containsKey(splitIndustryId))
                    splitIndustryIdToName.put(splitIndustryId,splitIndustry);

                if (!industryOccupationSplits.containsKey(pumsIndustryId))
                    industryOccupationSplits.put(pumsIndustryId, new HashMap<Integer,IndustryOccupationSplit>());
                if (!industryOccupationSplits.get(pumsIndustryId).containsKey(pumsOccupationId))
                    industryOccupationSplits.get(pumsIndustryId).put(pumsOccupationId,new IndustryOccupationSplit(pumsIndustryId,pumsOccupationId));
                industryOccupationSplits.get(pumsIndustryId).get(pumsOccupationId).addIndustrySplit(splitIndustryId,proportion);
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    //swallow
                }
            }
        }
    }

    Logger logger = Logger.getLogger(PumsToSplitIndustry.class);
    public int selectSplitIndustry(int pumsIndustry, int pumsOccupation) {
        if (!industryOccupationSplits.containsKey(pumsIndustry)) {
            logger.info("pums industry missing: " + pumsIndustry);
            return 0;
        }

        if (!industryOccupationSplits.get(pumsIndustry).containsKey(pumsOccupation))  {
            logger.info("pums occupation missing for industry: " + pumsIndustry + ", pumsOccupation: " + pumsOccupation);
            return 0;
        }
        
        return industryOccupationSplits.get(pumsIndustry).get(pumsOccupation).pickSplitIndustry();
    }

    private class IndustryOccupationSplit {
        private final int pumsIndustryId;
        private final int pumsOccupationId;
        private final Map<Integer,Double> splitIndustrySplit;
        private double[] proportionSplits;
        private int[] splitIndustryIds;

        public IndustryOccupationSplit(int pumsIndustryId, int pumsOccupationId) {
            this.pumsIndustryId = pumsIndustryId;
            this.pumsOccupationId = pumsOccupationId;
            splitIndustrySplit = new HashMap<Integer,Double>();
        }

        public void addIndustrySplit(int splitIndustry, double proportion) {
            if (splitIndustrySplit.containsKey(splitIndustry))
                throw new IllegalStateException(String.format("Multiple proportions values set for split industry %s for pums industry=%d and pums occupation=%d",splitIndustryIdToName.get(splitIndustry),pumsIndustryId,pumsOccupationId));
            splitIndustrySplit.put(splitIndustry,proportion);
        }

        private void checkProportions() {
            double total = 0.0;
            for (int id : splitIndustrySplit.keySet())
                total += splitIndustrySplit.get(id);
            if (total > 1.000001 || total < 0.999999)
                throw new IllegalStateException(String.format("Proportions for pums industry=%d and pums occupation=%d do not sum to 1.0 (%f)",pumsIndustryId,pumsOccupationId,total));
        }

        public void buildProportionSplits() {
            checkProportions();
            proportionSplits = new double[splitIndustrySplit.size()];
            splitIndustryIds = new int[proportionSplits.length];
            int counter = 0;
            double total = 0.0;
            for (int i : splitIndustrySplit.keySet()) {
                total += splitIndustrySplit.get(i);
                proportionSplits[counter] = total;
                splitIndustryIds[counter++] = i;
            }
        }

        public int pickSplitIndustry() {
            if (proportionSplits.length == 1) //short circuit for trivial case
                return splitIndustryIds[0];
            int edge = proportionSplits.length-1;
            double r = random.nextDouble();
            for (int i = 0; i < edge; i++)
                if (r < proportionSplits[i])
                    return splitIndustryIds[i];
            return splitIndustryIds[edge];
        }
    }


}

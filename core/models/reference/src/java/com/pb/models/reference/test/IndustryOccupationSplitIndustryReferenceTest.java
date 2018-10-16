package com.pb.models.reference.test;


import com.pb.models.reference.IndustryOccupationSplitIndustryReference;
import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;
import junit.textui.TestRunner;

/**
 * IndustryOccupationSplitIndustryReferenceTest is a class that ...
 *
 * @author Kimberly Grommes
 * @version 1.0, Dec 1, 2006
 *          Created by IntelliJ IDEA.
 */

public class IndustryOccupationSplitIndustryReferenceTest extends TestCase {
    IndustryOccupationSplitIndustryReference ref;
    boolean blnTLUMIP = true;
    boolean blnPrint = false;

    public IndustryOccupationSplitIndustryReferenceTest(String name) {
        super(name);
    }

    public void setUp() throws Exception {
        super.setUp();
        String file;
        if (blnTLUMIP) {
            file = "/models/IndustryOccupationSplitIndustryCorrespondenceTLUMIP.csv";
        } else {
            file = "/models/IndustryOccupationSplitIndustryCorrespondence.csv";
        }
        
        ref = new IndustryOccupationSplitIndustryReference(file);
        System.out.println("Number of unique Industries: " + ref.getNumOfIndustries());
        System.out.println("Number of unique Occupations: " + ref.getNumOfOccupations());
        System.out.println("Number of unique SplitIndustries: " + ref.getNumOfSplitIndustries());

        System.out.println("Max Industry Index: " + ref.getMaxIndustryIndex());
        System.out.println("Max Occupation Index: " + ref.getMaxOccupationIndex());
        System.out.println("Max SplitIndustry Index: " + ref.getMaxSplitIndustryIndex());

        if (blnTLUMIP && blnPrint) {
            System.out.println("Ag&Mining (2): " + ref.getIndustryIndexFromLabel("AGRICULTURE AND MINING"));
            System.out.println("Forestry&Logging (9): " + ref.getIndustryIndexFromLabel("FORESTRY AND LOGGING"));
            System.out.println("WholesaleTrade (26): " + ref.getIndustryIndexFromLabel("WHOLESALE TRADE"));

            System.out.println("1_ManPro (1): " + ref.getOccupationIndexFromLabel("1_ManPro"));
            System.out.println("5_RetSls (6): " + ref.getOccupationIndexFromLabel("5_RetSls"));
            System.out.println("2_PstSec (3): " + ref.getOccupationIndexFromLabel("2_PstSec"));

            System.out.println("Accomodations (1): " + ref.getSplitIndustryIndexFromLabel("ACCOMMODATIONS"));
            System.out.println("FoodLightInd (11): " + ref.getSplitIndustryIndexFromLabel("FOOD PRODUCTS-Light Industry"));
            System.out.println("HomebasedServices (20): " + ref.getSplitIndustryIndexFromLabel("HOMEBASED SERVICES"));

            System.out.println("Industry 0 (NoIndustry)" + ref.getIndustryLabelFromIndex(0));
            System.out.println("Industry 16 (LowerEducation)" + ref.getIndustryLabelFromIndex(16));
            System.out.println("Industry 25 (Transport)" + ref.getIndustryLabelFromIndex(25));

            System.out.println("Occupation 0 (1_ManPro)" + ref.getOccupationLabelFromIndex(1));
            System.out.println("Occupation 8 (7_NonOfc)" + ref.getOccupationLabelFromIndex(8));
            System.out.println("Occupation 5 (4_OthP&T)" + ref.getOccupationLabelFromIndex(5));

            System.out.println("SplitIndustry 4 (Comm&Util-LightInd)" + ref.getSplitIndustryLabelFromIndex(4));
            System.out.println("SplitIndustry 15 (GovAdminOffice)" + ref.getSplitIndustryLabelFromIndex(15));
            System.out.println("SplitIndustry 15 (OtherNonDurOffice)" + ref.getSplitIndustryLabelFromIndex(30));

            System.out.println("SplitIndustryIndex for Ag&Mining - ManPro (2,3)" + ref.getSplitIndustryIndex(2,1));
            System.out.println("SplitIndustryIndex for Elect&InstLightInd - Health (7,8)" + ref.getSplitIndustryIndex(5,2));
            System.out.println("SplitIndustryIndex for Accom - PostSec (1)" + ref.getSplitIndustryIndex(1,3));
            
        } else if (blnPrint) {

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

    public void tearDown() throws Exception {
        super.tearDown();
    }


    public static Test suite() {
        return new TestSuite(IndustryOccupationSplitIndustryReferenceTest.class);
    }

    public static void main(String[] args) {
        new TestRunner().doRun(suite());
    }

    public void testSplitIndustryIndexforRandomness() throws Exception {
        int intResult;
        int intTwos = 0;
        int intThrees = 0;
        int intSomething = 0;
        System.out.println("Should be 2 or 3.");
        for (int i = 0; i < 1000; i++) {
            intResult = ref.getSplitIndustryIndex(2,0);
            if (intResult == 2) {
                intTwos += 1;
            } else if (intResult == 3) {
                intThrees += 1;
            } else
                intSomething += 1;
            }
        System.out.println("Twos: " + intTwos + " Threes: " + intThrees + " Else: " + intSomething + ".");

        }
    
}

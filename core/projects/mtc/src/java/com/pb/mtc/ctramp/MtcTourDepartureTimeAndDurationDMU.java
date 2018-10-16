package com.pb.mtc.ctramp;

import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TourDepartureTimeAndDurationDMU;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 14, 2008
 * Time: 9:14:30 AM
 * To change this template use File | Settings | File Templates.
 */
public class MtcTourDepartureTimeAndDurationDMU extends TourDepartureTimeAndDurationDMU {

    public static Logger logger = Logger.getLogger(MtcTourDepartureTimeAndDurationDMU.class);


    public MtcTourDepartureTimeAndDurationDMU( ModelStructure modelStructure ){
    	super( modelStructure );
    	setupMethodIndexMap();
    }

    public int getHhIncomeInDollars() {
    	return household.getIncomeInDollars(); 
    }

    public int getIncomeHigherThan100k () {
    	if (household.getIncomeInDollars() > 100000) return 1; 
    	else return 0; 
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return household.getHAnalyst();
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst(){
    	return person.getPAnalyst();
    }
    
    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getOriginZone", 0 );
        methodIndexMap.put( "getDestinationZone", 1 );
        methodIndexMap.put( "getIncomeInThousands", 2 );
        methodIndexMap.put( "getIncomeHigherThan100k", 3 );
        methodIndexMap.put( "getHhIncomeInDollars", 4 );
        methodIndexMap.put( "getOriginAreaType", 5 );
        methodIndexMap.put( "getDestinationAreaType", 6 );
        methodIndexMap.put( "getFullTimeWorker", 7 );
        methodIndexMap.put( "getPartTimeWorker", 8 );
        methodIndexMap.put( "getUniversityStudent", 9 );
        methodIndexMap.put( "getStudentDrivingAge", 10 );
        methodIndexMap.put( "getNonWorker", 11 );
        methodIndexMap.put( "getRetired", 12 );
        methodIndexMap.put( "getAllAdultsFullTimeWorkers", 13 );
        methodIndexMap.put( "getTourPurposeIsShopping", 14 );
        methodIndexMap.put( "getTourPurposeIsEatOut", 15 );
        methodIndexMap.put( "getTourPurposeIsMaint", 16 );
        methodIndexMap.put( "getTourPurposeIsDiscr", 17 );
        methodIndexMap.put( "getSubtourPurposeIndex", 18 );
        methodIndexMap.put( "getAdultsInTour", 19 );
        methodIndexMap.put( "getChildrenInTour", 20 );
        methodIndexMap.put( "getPreschoolPredrivingInTour", 21 );
        methodIndexMap.put( "getUnivInTour", 22 );
        methodIndexMap.put( "getAllWorkFull", 23 );
        methodIndexMap.put( "getPartyComp", 24 );
        methodIndexMap.put( "getPersonNonMandatoryTotalWithEscort", 25 );
        methodIndexMap.put( "getHhJointTotal", 26 );
        methodIndexMap.put( "getPersonMandatoryTotal", 27 );
        methodIndexMap.put( "getPersonJointTotal", 28 );
        methodIndexMap.put( "getFirstTour", 29 );
        methodIndexMap.put( "getSubsequentTour", 30 );
        methodIndexMap.put( "getWorkAndSchoolToursByWorker", 31 );
        methodIndexMap.put( "getWorkAndSchoolToursByStudent", 32 );
        methodIndexMap.put( "getModeChoiceLogsumAlt", 33 );
        methodIndexMap.put( "getPrevTourEndsThisDepartureHourAlt", 34 );
        methodIndexMap.put( "getPrevTourBeginsThisArrivalHourAlt", 35 );
        methodIndexMap.put( "getAdjWindowBeforeThisHourAlt", 36 );
        methodIndexMap.put( "getAdjWindowAfterThisHourAlt", 37 );
        methodIndexMap.put( "getEndOfPreviousTour", 38 );
        methodIndexMap.put( "getPersonNonMandatoryTotalNoEscort", 39 );
        methodIndexMap.put( "getTourPurposeIsVisit", 40 );
        methodIndexMap.put( "getStudentNonDrivingAge", 41 );
        methodIndexMap.put( "getPersonEscortTotal", 42 );
        methodIndexMap.put( "getPersonIsAdult", 43 );
        methodIndexMap.put( "getNumChildrenInHh", 44 );
        methodIndexMap.put( "getRemainingHoursAvailableAlt", 45 );
        methodIndexMap.put( "getRemainingInmToursToAvailableHoursRatioAlt", 46 );
        methodIndexMap.put( "getTourCategoryIsJoint", 47 );
        methodIndexMap.put( "getAdultInTour", 48 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 49 );
        methodIndexMap.put( "getPAnalyst", 50 );
    }
    

    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getOriginZone();
            case 1: return getDestinationZone();
            case 2: return getIncomeInThousands();
            case 3: return getIncomeHigherThan100k();
            case 4: return getHhIncomeInDollars();
            case 5: return getOriginAreaType();
            case 6: return getDestinationAreaType();
            case 7: return getFullTimeWorker();
            case 8: return getPartTimeWorker();
            case 9: return getUniversityStudent();
            case 10: return getStudentDrivingAge();
            case 11: return getNonWorker();
            case 12: return getRetired();
            case 13: return getAllAdultsFullTimeWorkers();
            case 14: return getTourPurposeIsShopping();
            case 15: return getTourPurposeIsEatOut();
            case 16: return getTourPurposeIsMaint();
            case 17: return getTourPurposeIsDiscr();
            case 18: return getSubtourPurposeIndex();
            case 19: return getAdultsInTour();
            case 20: return getChildrenInTour();
            case 21: return getPreschoolPredrivingInTour();
            case 22: return getUnivInTour();
            case 23: return getAllWorkFull();
            case 24: return getPartyComp();
            case 25: return getPersonNonMandatoryTotalWithEscort();
            case 26: return getHhJointTotal();
            case 27: return getPersonMandatoryTotal();
            case 28: return getPersonJointTotal();
            case 29: return getFirstTour();
            case 30: return getSubsequentTour();
            case 31: return getWorkAndSchoolToursByWorker();
            case 32: return getWorkAndSchoolToursByStudent();
            case 33: return getModeChoiceLogsumAlt( arrayIndex );
            case 34: return getPrevTourEndsThisDepartureHourAlt( arrayIndex );
            case 35: return getPrevTourBeginsThisArrivalHourAlt( arrayIndex );
            case 36: return getAdjWindowBeforeThisHourAlt( arrayIndex );
            case 37: return getAdjWindowAfterThisHourAlt( arrayIndex );
            case 38: return getEndOfPreviousTour();
            case 39: return getPersonNonMandatoryTotalNoEscort();
            case 40: return getTourPurposeIsVisit();
            case 41: return getStudentNonDrivingAge();
            case 42: return getPersonEscortTotal();
            case 43: return getPersonIsAdult();
            case 44: return getNumChildrenInHh();
            case 45: return getRemainingHoursAvailableAlt( arrayIndex );
            case 46: return getRemainingInmToursToAvailableHoursRatioAlt( arrayIndex );
            case 47: return getTourCategoryIsJoint();
            case 48: return getAdultInTour();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 49: return getHAnalyst();
            case 50: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }


}

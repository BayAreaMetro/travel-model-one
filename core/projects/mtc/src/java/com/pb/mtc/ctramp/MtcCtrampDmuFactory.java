package com.pb.mtc.ctramp;

import java.io.Serializable;

import com.pb.models.ctramp.AccConstantsDMU;
import com.pb.models.ctramp.AccessibilityDMU;
import com.pb.models.ctramp.AtWorkSubtourFrequencyDMU;
import com.pb.models.ctramp.AutoOwnershipChoiceDMU;
import com.pb.models.ctramp.CoordinatedDailyActivityPatternDMU;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.DestChoiceDMU;
import com.pb.models.ctramp.FreeParkingChoiceDMU;
import com.pb.models.ctramp.IndividualMandatoryTourFrequencyDMU;
import com.pb.models.ctramp.IndividualNonMandatoryTourFrequencyDMU;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.ParkingChoiceDMU;
import com.pb.models.ctramp.StopDCSoaDMU;
import com.pb.models.ctramp.StopFrequencyDMU;
import com.pb.models.ctramp.StopLocationDMU;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.JointTourFrequencyDMU;
import com.pb.models.ctramp.TourDepartureTimeAndDurationDMU;
import com.pb.models.ctramp.TripModeChoiceDMU;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 9, 2008
 * Time: 3:16:34 PM
 * To change this template use File | Settings | File Templates.
 */
public class MtcCtrampDmuFactory implements CtrampDmuFactoryIf, Serializable {

    TazDataIf tazDataHandler;
    ModelStructure modelStructure;
    

    public MtcCtrampDmuFactory( TazDataIf tazDataHandler, ModelStructure modelStructure ) {
        this.tazDataHandler = tazDataHandler;
        this.modelStructure = modelStructure;
    }


    
    public AccessibilityDMU getAccessibilityDMU() {
        return new AccessibilityDMU();
    }


    public AccConstantsDMU getAccConstantsDMU() {
        return new AccConstantsDMU();
    }


    public AutoOwnershipChoiceDMU getAutoOwnershipDMU() {
        return new MtcAutoOwnershipChoiceDMU( tazDataHandler );
    }


    public FreeParkingChoiceDMU getFreeParkingChoiceDMU() {
        return new MtcFreeParkingChoiceDMU();
    }


    public CoordinatedDailyActivityPatternDMU getCoordinatedDailyActivityPatternDMU() {
        return new MtcCoordinatedDailyActivityPatternDMU( tazDataHandler );
    }


    public DcSoaDMU getDcSoaDMU() {
        return new MtcDcSoaDMU( tazDataHandler );
    }


    public DestChoiceDMU getDestChoiceDMU() {
        return new MtcDestChoiceDMU( tazDataHandler, modelStructure );
    }


    public ModeChoiceDMU getModeChoiceDMU() {
        return new MtcModeChoiceDMU( tazDataHandler, modelStructure );
    }


    public IndividualMandatoryTourFrequencyDMU getIndividualMandatoryTourFrequencyDMU() {
        return new MtcIndividualMandatoryTourFrequencyDMU();
    }

    
    public TourDepartureTimeAndDurationDMU getTourDepartureTimeAndDurationDMU() {
        return new MtcTourDepartureTimeAndDurationDMU( modelStructure );
    }

    
    public AtWorkSubtourFrequencyDMU getAtWorkSubtourFrequencyDMU() {
        return new MtcAtWorkSubtourFrequencyDMU( modelStructure );
    }

    
    public JointTourFrequencyDMU getJointTourFrequencyDMU() {
        return new MtcJointTourFrequencyDMU( modelStructure );
    }

    
    public IndividualNonMandatoryTourFrequencyDMU getIndividualNonMandatoryTourFrequencyDMU() {
        return new MtcIndividualNonMandatoryTourFrequencyDMU();
    }

    
    public StopFrequencyDMU getStopFrequencyDMU() {
        return new MtcStopFrequencyDMU( modelStructure );
    }

    
    public StopDCSoaDMU getStopDCSoaDMU() {
        return new MtcStopDCSoaDMU(tazDataHandler, modelStructure);
    }
    
    
    public StopLocationDMU getStopLocationDMU() {
        return new MtcStopLocationDMU(tazDataHandler, modelStructure);
    }

    
    public TripModeChoiceDMU getTripModeChoiceDMU() {
        return new MtcTripModeChoiceDMU( tazDataHandler, modelStructure );
    }

    
    public ParkingChoiceDMU getParkingChoiceDMU() {
        return new MtcParkingChoiceDMU( tazDataHandler );
    }

}

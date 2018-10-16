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
package com.pb.common.summit;

import org.apache.log4j.Logger;
import java.util.Vector;
import java.io.IOException;

/**
 * Merge the data from multiple FTA Summit .ubn files into one
 * aggregate .ubn file.  
 * 
 * @author Charlton
 */
public class MergeSummitFiles {
	
    protected static Logger logger = Logger.getLogger("com.pb.common.util");

    int mZones = 0;
    int mSegments = 0;
    
    /**
     * Constructor.  Open and merge the files.
     */
    public MergeSummitFiles(String[] filenames) {

        // open output file
        SummitFileWriter out = new SummitFileWriter(filenames[0]);
        
        // create vector of input files
        Vector infiles = new Vector();
        for (int i=1; i<filenames.length; ++i)
            infiles.add(new SummitFileReader(filenames[i]));
        
        // set up headers
        processHeaders(infiles, out);
        
        // loop on the data records
        processRecords(infiles, out);
        
		// Files will close automatically when program exits.
		// Can't close them in code because SummitFileWriter doesn't have
		// a close-file method.
	}

	/**
	 * Read the headers of the input summit files, and use the header
     * as a template for creating the new summit output file.
     *
	 * @param in Vector of SummitFileReaders to be summarized 
	 * @param out Output file
	 */
	void processHeaders(Vector in, SummitFileWriter out) {        
		try {
			// Read all the headers.  Must read the header from each file
			// so that the random-access file is cued to the right location.
			SummitHeader header = null;
			for (int i=0; i<in.size(); i++) {
		        header = ((SummitFileReader)in.elementAt(i)).getHeader();
		    }

			// And write the header to the output file
			mZones = header.getZones();
			mSegments = header.getMarketSegments();
			out.writeHeader(header);
			
		} catch (IOException ioe) {
			ioe.printStackTrace();
			System.exit(1);
		}
    }
    
	/**
     * Read the records from the input summit files, and summarize
	 * their results.  Then output aggregate summit data.
	 *
	 * @param in Vector of SummitFileReaders to be summarized 
	 * @param out Output file
	 */
	void processRecords(Vector in, SummitFileWriter out) {        

		// Create array for storing a set of summit records
		SummitRecord[] recs = new SummitRecord[in.size()];

		try {
			// Loop on i, j, marget segment, and inputfile 
			for (int iz = 1; iz <= mZones; iz++) {
				for (int jz = 1; jz <= mZones; jz++) {
					for (int sg = 1; sg <= mSegments; sg++) {
						for (int i=0; i<in.size(); i++) {
							recs[i] = ((SummitFileReader)in.elementAt(i)).getSpecificRecord(iz,jz,sg);
						}
						SummitRecord mrgRec = mergeRecords(recs);
						if (mrgRec != null) {
//							if (iz==756 && jz==57) {
//								System.out.println("Found it");
//							}
							mrgRec.setPtaz((short)iz);
							mrgRec.setAtaz((short)jz);
							mrgRec.setMarket((short)sg);
	
							out.writeRecord(mrgRec);
						}
					}
				}
				System.out.print(" "+iz);
				if (iz % 19 == 18) System.out.println();

			}
			System.out.println("\nDone.");

		} catch (IOException ioe) {
		    System.err.println("\n Trouble!\n");
		    ioe.printStackTrace();
		    System.exit(1);
		}
	}

	/**
	 * Merge an array of summit records.
	 * @param recs Array of SummitRecords.  Individual array elements must 
	 * be either valid instances of SummitRecord, or null.  Null elements
	 * will be ignored.  
	 * @return Merged summit record
	 */
	SummitRecord mergeRecords(SummitRecord[] recs) {
		// Create merged record placeholder
		SummitRecord mrgRec = new ConcreteSummitRecord();

		float mrgTrips = 0;
		float mrgMTrips = 0;
		float mrgUtil = 0;
		float mrgTrnWlk = 0;
		float mrgTrnDrv = 0;
		float mrgCanWalk = 0;
		float mrgMustDrive = 0;

		int testTrnTrips = 0;
		
		// sum the relevant fields
		for (int x=0; x<recs.length; x++) {

		    // Check to see if this i,j,s pair exists for each file
		    if (recs[x] != null) {
				mrgTrips  += recs[x].getTrips();

		        float trips = recs[x].getMotorizedTrips();
				mrgMTrips += trips;

//				if (trips > 0)
//					testTrnTrips++;

				// weight the sums for the utility and shares by motorized trips
				mrgUtil   += recs[x].getExpAuto() * trips;
				mrgTrnWlk += recs[x].getTransitShareOfWalkTransit() * trips;
				mrgTrnDrv += recs[x].getTransitShareOfDriveTransitOnly() * trips;

				// Even the geographic segments are averaged
				mrgCanWalk   += trips * recs[x].getWalkTransitAvailableShare();
				mrgMustDrive += trips * recs[x].getDriveTransitOnlyShare();
		    }
		}
		
		// Make sure there were some trips in this interchange; otherwise
		// we can skip it!
		if (mrgTrips == 0)
		    return null;
		
		// create the weighted averages
		mrgUtil      = mrgUtil / mrgMTrips;
		mrgTrnWlk    = mrgTrnWlk / mrgMTrips;
		mrgTrnDrv    = mrgTrnDrv / mrgMTrips;

		mrgCanWalk   = mrgCanWalk / mrgMTrips;
		mrgMustDrive = mrgMustDrive / mrgMTrips;

		// And un-scale the transit shares.  Required since the canwalk/mustdrive
		// factors above would otherwise be double-weighted.  Bad!
		if (mrgMustDrive > 0) {
			mrgTrnDrv = mrgTrnDrv / mrgMustDrive;		
//			mrgMustDrive = 1;
		}

		if (mrgCanWalk > 0) {
			mrgTrnWlk = mrgTrnWlk / mrgCanWalk;
//			mrgCanWalk = 1;
		}


		// Divide by the number of files 
		mrgTrips = mrgTrips / recs.length;
		mrgMTrips = mrgMTrips / recs.length;
		
		// populate the record
		mrgRec.setTrips(mrgTrips);
		mrgRec.setMotorizedTrips(mrgMTrips);
		mrgRec.setExpAuto(mrgUtil);

		mrgRec.setWalkTransitAvailableShare(mrgCanWalk);
		mrgRec.setDriveTransitOnlyShare(mrgMustDrive);

		mrgRec.setTransitShareOfWalkTransit(mrgTrnWlk);
		mrgRec.setTransitShareOfDriveTransitOnly(mrgTrnDrv);

		return mrgRec;
	}
	

    /**
     * Entry code.
     */
    public static void main(String[] args) {
        if (args.length < 2 ) {
            System.err.println("java MergeSummit [output] [infile1] [infile2] ...");
            System.exit(1);
        }

        new MergeSummitFiles(args);
    }

}

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
 */
/*
 * Created on May 3, 2005
 * Calculate statistics from SynPop object
 */
package com.pb.models.synpopV3;
import java.util.Vector;

import org.apache.log4j.Logger;

//import com.pb.common.matrix.NDimensionalMatrix;
//import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class SynPopValidationStatistics {
	
	protected boolean logDebug=false;
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected Vector SynPop;
	//1D validation statistic ID, 2D TAZ
	protected int [][] vStatistics;
	protected int numberOfInternalZones;
	protected int NoStatistics;
	
	public SynPopValidationStatistics(Vector SynPop){
		this.SynPop=SynPop;
		numberOfInternalZones = PopulationSynthesizer.numberOfInternalZones;
		NoStatistics=new Integer(PropertyParser.getPropertyByName("NoValidationStatistics")).intValue();
		vStatistics=makeVStatistics();
	}
	
	public int [][] getVStatistics(){
		return vStatistics;
	}
	
	public float [][] getVStatisticsFloat(){
		float [][] result=new float[NoStatistics][numberOfInternalZones];
		for(int i=0; i<NoStatistics; i++){
			for(int j=0; j<numberOfInternalZones; j++){
				result[i][j]=vStatistics[i][j];
			}
		}
		return result;
	}
	
	public int getVStatistics(int i, int j){
		return vStatistics[i][j];
	}
	
	public int getNoStatistics(){
		return NoStatistics;
	}
	
	
	protected int [][] makeVStatistics(){
		
		int [][] result=new int[NoStatistics][numberOfInternalZones];
				
		DrawnHH currentHH=null;
		DerivedPerson currentPerson=null;
		int currentTAZ=-1;
		int current_hfamily=-1;
//JB added next line
		int current_hunittype=-1;
		int current_persons=-1;
		int current_hhagecat=-1;
		int current_hsizecat=-1;
		int current_hNOCcat=-1;
		int current_h0005=-1;
		int current_h0611=-1;
		int current_h1215=-1;
		int current_h1617=-1;
		int current_h6579=-1;
		int current_h80up=-1;
		int current_h0017=-1;
		int current_h6580up=-1;
		int current_hwrkrcat=-1;
		int current_hworkers=-1;
		int current_hinccat1=-1;
		int current_hinccat2=-1;
		int current_htypdwel=-1;
		int current_hownrent=-1;
		int current_psex=-1;
		int current_page=-1;
		int current_pagecat=-1;
		int current_pmarstat=-1;
		int current_phispan=-1;
		int current_prace=-1;
		int current_pweeks=-1;
		int current_phrs=-1;
		int current_pESR=-1;
		int current_pstudent=-1;
		int current_phrelate=-1;
		int current_ppoverty=-1;

		for(int i=0; i<SynPop.size(); i++){
			
			currentHH=(DrawnHH)SynPop.get(i);
			currentTAZ=currentHH.getHHAttr("TAZ");
			current_persons=currentHH.getHHAttr("PERSONS");
			current_hNOCcat=currentHH.getHHAttr("hNOCcat");
			current_hfamily=currentHH.getHHAttr("hfamily");
//JB added next line
			current_hunittype=currentHH.getHHAttr("hunittype");
			current_hhagecat=currentHH.getHHAttr("hhagecat");
			current_hsizecat=currentHH.getHHAttr("hsizecat");
			current_h0005=currentHH.getHHAttr("h0005");
			current_h0611=currentHH.getHHAttr("h0611");
			current_h1215=currentHH.getHHAttr("h1215");
			current_h1617=currentHH.getHHAttr("h1617");
			current_h0017=current_h0005+current_h0611+current_h1215+current_h1617;
			current_h6579=currentHH.getHHAttr("h6579");
			current_h80up=currentHH.getHHAttr("h80up");
			current_h6580up=current_h6579+current_h80up;
			current_hwrkrcat=currentHH.getHHAttr("hwrkrcat");
			current_hworkers=currentHH.getHHAttr("hworkers");
			current_hinccat1=currentHH.getHHAttr("hinccat1");
			current_hinccat2=currentHH.getHHAttr("hinccat2");
			current_htypdwel=currentHH.getHHAttr("htypdwel");
			current_hownrent=currentHH.getHHAttr("hownrent");
			
//JB    added ( )&&current_hunittype==0 to next line
			if((current_hfamily==1||current_hfamily==2)&&current_hunittype==0){
				
				//set universe 1
				result[0][currentTAZ-1]++;
				
				if(current_hfamily==2){
					result[1][currentTAZ-1]++;
				}
				if(current_hfamily==1){
					result[2][currentTAZ-1]++;
				}
				if(current_hhagecat==1){
					result[3][currentTAZ-1]++;
				}
				if(current_hhagecat==2){
					result[4][currentTAZ-1]++;
				}
				if(current_hsizecat==1){
					result[5][currentTAZ-1]++;
				}
				if(current_hsizecat==2){
					result[6][currentTAZ-1]++;
				}
				if(current_hsizecat==3){
					result[7][currentTAZ-1]++;
				}
				if(current_hsizecat==4){
					result[8][currentTAZ-1]++;
				}
				if(current_persons==5){
					result[9][currentTAZ-1]++;
				}
				if(current_persons==6){
					result[10][currentTAZ-1]++;
				}
				if(current_persons>=7){
					result[11][currentTAZ-1]++;
				}
				if(current_hsizecat==5){
					result[12][currentTAZ-1]++;
				}
				if(current_hhagecat==1&&current_hfamily==2){
					result[13][currentTAZ-1]++;
				}
				if(current_hhagecat==2&&current_hfamily==2){
					result[14][currentTAZ-1]++;
				}
				if(current_hhagecat==1&&current_hfamily==1){
					result[15][currentTAZ-1]++;
				}
				if(current_hhagecat==2&&current_hfamily==1){
					result[16][currentTAZ-1]++;
				}
				if(current_hfamily==2&&current_hNOCcat==1){
					result[17][currentTAZ-1]++;
				}
				if(current_hfamily==2&&current_hNOCcat==0){
					result[18][currentTAZ-1]++;
				}
//JB  		if(current_hfamily==2&&current_h0017>1){
				if(current_hfamily==2&&current_h0017>0){
					result[19][currentTAZ-1]++;
				}
				if(current_hfamily==2&&current_h0017==0){
					result[20][currentTAZ-1]++;
				}
//JB			if(current_hfamily==1&&current_h0017>1){
				if(current_hfamily==1&&current_h0017>0){
					result[21][currentTAZ-1]++;
				}
				if(current_hfamily==1&&current_h0017==0){
					result[22][currentTAZ-1]++;
				}
				if(current_h6580up>0){
					result[23][currentTAZ-1]++;
				}
				if(current_h6580up==0){
					result[24][currentTAZ-1]++;
				}
				if(current_hsizecat==1&&current_h6580up>0){
					result[25][currentTAZ-1]++;
				}
				if(current_hfamily==2&&current_h6580up>0){
					result[26][currentTAZ-1]++;
				}
				if(current_hfamily==1&&current_persons>1&&current_h6580up>0){
					result[27][currentTAZ-1]++;
				}
				if(current_hsizecat==1&&current_h6580up==0){
					result[28][currentTAZ-1]++;
				}
				if(current_hfamily==2&&current_h6580up==0){
					result[29][currentTAZ-1]++;
				}
				if(current_hfamily==1&&current_persons>1&&current_h6580up==0){
					result[30][currentTAZ-1]++;
				}
				if(current_hwrkrcat==0){
					result[31][currentTAZ-1]++;					
				}
				if(current_hwrkrcat==1){
					result[32][currentTAZ-1]++;					
				}
				if(current_hwrkrcat==2){
					result[33][currentTAZ-1]++;					
				}
				if(current_hworkers==3){
					result[34][currentTAZ-1]++;					
				}
				if(current_hworkers>=4){
					result[35][currentTAZ-1]++;					
				}
				if(current_hwrkrcat==3){
					result[36][currentTAZ-1]++;					
				}
				if(current_hinccat1==1){
					result[37][currentTAZ-1]++;					
				}
				if(current_hinccat1==2){
					result[38][currentTAZ-1]++;					
				}
				if(current_hinccat1==3){
					result[39][currentTAZ-1]++;					
				}
				if(current_hinccat1==4){
					result[40][currentTAZ-1]++;					
				}
				if(current_hinccat2==1){
					result[41][currentTAZ-1]++;					
				}
				if(current_hinccat2==2){
					result[42][currentTAZ-1]++;					
				}
				if(current_hinccat2==3){
					result[43][currentTAZ-1]++;					
				}
				if(current_hinccat2==4){
					result[44][currentTAZ-1]++;					
				}
				if(current_hinccat2==5){
					result[45][currentTAZ-1]++;					
				}
				if(current_hinccat2==6){
					result[46][currentTAZ-1]++;					
				}
				if(current_hinccat2==7){
					result[47][currentTAZ-1]++;					
				}
				if(current_hinccat2==8){
					result[48][currentTAZ-1]++;					
				}
				if(current_hinccat1==1||current_hinccat1==2){
					result[49][currentTAZ-1]++;					
				}
				if(current_htypdwel==1){
					result[50][currentTAZ-1]++;
				}
				if(current_htypdwel==2){
					result[51][currentTAZ-1]++;
				}
				if(current_htypdwel==3){
					result[52][currentTAZ-1]++;
				}
				if(current_hownrent==1){
					result[53][currentTAZ-1]++;
				}
				if(current_hownrent==2){
					result[54][currentTAZ-1]++;
				}
				
				//set universe 2
				result[55][currentTAZ-1]+=current_persons;
				
				if(current_hfamily==2){
					result[56][currentTAZ-1]+=current_persons;
				}
   			    if(current_hfamily==1){
					result[57][currentTAZ-1]+=current_persons;
				}
				for(int j=0; j<current_persons; j++){
					currentPerson= (currentHH.getDerivedHH()).getPerson(j+1);
					current_ppoverty=currentPerson.getPAttr("POVERTY");
					if(current_ppoverty>=1&&current_ppoverty<100){
						result[58][currentTAZ-1]++;
					}
					
				}
			}
			
			if(current_hfamily==2){
				
				//set universe 3
				result[59][currentTAZ-1]+=current_persons;
				
				for(int j=0; j<current_persons; j++){
					
					currentPerson= (currentHH.getDerivedHH()).getPerson(j+1);
					current_phrelate=currentPerson.getPAttr("RELATE");
					
					if(current_phrelate==1){
						result[60][currentTAZ-1]++;
					}
					if(current_phrelate==2){
						result[61][currentTAZ-1]++;
					}
					if(current_phrelate>=3&&current_phrelate<=5){
						result[62][currentTAZ-1]++;
					}
					if(current_phrelate>=6&&current_phrelate<=21){
						result[63][currentTAZ-1]++;
					}
					if(current_phrelate>=17&&current_phrelate<=21){
						result[64][currentTAZ-1]++;
					}
				}
			}
			
			//set universe 4
			result[65][currentTAZ-1]+=current_persons;
			
			for(int j=0; j<current_persons; j++){
				
				currentPerson= (currentHH.getDerivedHH()).getPerson(j+1);
				current_psex=currentPerson.getPAttr("SEX");
				current_page=currentPerson.getPAttr("AGE");
				current_prace=currentPerson.getPAttr("RACE1");
				current_pweeks=currentPerson.getPAttr("WEEKS");
				current_phrs=currentPerson.getPAttr("HOURS");
				current_pESR=currentPerson.getPAttr("ESR");
				current_pmarstat=currentPerson.getPAttr("MSP");
				current_pagecat=currentPerson.getPAttr("pagecat");
				current_phispan=currentPerson.getPAttr("phispan");
				current_pstudent=currentPerson.getPAttr("pstudent");
				
				if(current_psex==1){
					result[66][currentTAZ-1]++;
				}
				if(current_psex==2){
					result[67][currentTAZ-1]++;
				}
				if(current_page>=0&&current_page<=2){
					result[68][currentTAZ-1]++;
				}
				if(current_pagecat==0){
					result[69][currentTAZ-1]++;
				}
				if(current_pagecat==1){
					result[70][currentTAZ-1]++;
				}
				if(current_pagecat==2){
					result[71][currentTAZ-1]++;
				}
				if(current_pagecat==3){
					result[72][currentTAZ-1]++;
				}
				if(current_pagecat==4){
					result[73][currentTAZ-1]++;
				}
				if(current_pagecat==5){
					result[74][currentTAZ-1]++;
				}
				if(current_pagecat==6){
					result[75][currentTAZ-1]++;
				}
				if(current_pagecat==7){
					result[76][currentTAZ-1]++;
				}
				if(current_pagecat==8){
					result[77][currentTAZ-1]++;
				}
				if(current_pagecat==9){
					result[78][currentTAZ-1]++;
				}
				if(current_pagecat>=0&&current_pagecat<=3){
					result[79][currentTAZ-1]++;
				}
				if(current_pagecat>=4&&current_pagecat<=7){
					result[80][currentTAZ-1]++;
				}
				if(current_pagecat>=8&&current_pagecat<=9){
					result[81][currentTAZ-1]++;
				}
				if(current_pmarstat==1){
					result[82][currentTAZ-1]++;
				}
				if(current_phispan>=2){
					result[83][currentTAZ-1]++;
				}
				if(current_prace==1){
					result[84][currentTAZ-1]++;
				}
				if(current_prace==2){
					result[85][currentTAZ-1]++;
				}
				if(current_prace>=3&&current_prace<=5){
					result[86][currentTAZ-1]++;
				}
				if(current_prace==6){
					result[87][currentTAZ-1]++;
				}
				if(current_prace==7){
					result[88][currentTAZ-1]++;
				}
				if(current_prace==8||current_prace==9){
					result[89][currentTAZ-1]++;
				}
				
				if(current_prace>=1&&current_prace<=8){
					//set universe 5
					result[90][currentTAZ-1]++;
				}
				result[91][currentTAZ-1]=result[84][currentTAZ-1];
				result[92][currentTAZ-1]=result[85][currentTAZ-1];
				result[93][currentTAZ-1]=result[86][currentTAZ-1];
				result[94][currentTAZ-1]=result[87][currentTAZ-1];
				result[95][currentTAZ-1]=result[88][currentTAZ-1];
				if(current_prace==8){
					result[96][currentTAZ-1]++;
				}
				
				if(current_pweeks>=27){
					//set universe 6
					result[97][currentTAZ-1]++;
					
//					JB			if(current_pweeks>=35){
					if(current_pweeks>=27&&current_phrs>=35){
						result[98][currentTAZ-1]++;
					}

//					JB			if(current_pweeks>=15&&current_pweeks<35){
					if(current_pweeks>=27&&current_phrs>=15&&current_phrs<35){
						result[99][currentTAZ-1]++;
					}

//					JB			if(current_pweeks>=1&&current_pweeks<15){
					if(current_pweeks>=27&&current_phrs>=1&&current_phrs<15){
						result[100][currentTAZ-1]++;
					}
				}
							
				if(current_page>=16){
					//set universe 7
					result[101][currentTAZ-1]++;
					if(current_pESR==1||current_pESR==2){
						result[102][currentTAZ-1]++;
					}
					if(current_pESR==4||current_pESR==5){
						result[103][currentTAZ-1]++;
					}
					if(current_pESR==3){
						result[104][currentTAZ-1]++;
					}
					if(current_pESR==6){
						result[105][currentTAZ-1]++;
					}
				}
				if(current_page>=3){
					//set universe 8
					result[106][currentTAZ-1]++;
					
					if(current_pstudent==1){
						result[107][currentTAZ-1]++;
					}
					if(current_pstudent==2){
						result[108][currentTAZ-1]++;
					}
				}
			}
            
            // only execute if additional validation stats are desired-gde 
            if (NoStatistics > 109) {                
                
                int current_hmultiunit=-1;
                current_hmultiunit=currentHH.getHHAttr("hmultiunit");
                
                //set universe 9--households
                if((current_hfamily==1||current_hfamily==2)&&current_hunittype==0){
                    
                    result[109][currentTAZ-1]++;
                    
                    if(current_hmultiunit==0){
                        result[110][currentTAZ-1]++;
                    }
                    if(current_hmultiunit==1){
                        result[111][currentTAZ-1]++;
                    }
                    if(current_hsizecat==1){
                        result[112][currentTAZ-1]++;
                    }
                    if(current_hsizecat==2){
                        result[113][currentTAZ-1]++;
                    }
                    if(current_hsizecat==3){
                        result[114][currentTAZ-1]++;
                    }
                    if(current_hsizecat==4){
                        result[115][currentTAZ-1]++;
                    }
                    if(current_hsizecat==5){
                        result[116][currentTAZ-1]++;
                    }
                    if(current_hwrkrcat==0){
                        result[117][currentTAZ-1]++;                 
                    }
                    if(current_hwrkrcat==1){
                        result[118][currentTAZ-1]++;                 
                    }
                    if(current_hwrkrcat==2){
                        result[119][currentTAZ-1]++;                 
                    }
                    if(current_hwrkrcat==3){
                        result[120][currentTAZ-1]++;                 
                    }
                    if(current_hinccat2==1 || current_hinccat2==2 || current_hinccat2==3){
                        result[121][currentTAZ-1]++;                 
                    }
                    if(current_hinccat2==4 || current_hinccat2==5 || current_hinccat2==6){
                        result[122][currentTAZ-1]++;                 
                    } 
                    if(current_hinccat2==7 || current_hinccat2==8){
                        result[123][currentTAZ-1]++;                 
                    }
                    if(current_hinccat2==9){
                        result[124][currentTAZ-1]++;                 
                    }                  
                    if(current_hhagecat==1){
                        result[125][currentTAZ-1]++;
                    }
                    if(current_hhagecat==2){
                        result[126][currentTAZ-1]++;
                    }
                    if(current_hNOCcat==1){
                        result[127][currentTAZ-1]++;
                    }
                    if(current_hNOCcat==0){
                        result[128][currentTAZ-1]++;
                    }                  
                }

                //set universe 10-all persons
                result[129][currentTAZ-1]+=current_persons;
                
                if (current_hunittype==0) {
                    result[130][currentTAZ-1]+=current_persons;
                }
                if (current_hunittype>0) {
                    result[131][currentTAZ-1]+=current_persons;
                }
                
                for(int j=0; j<current_persons; j++){
                    currentPerson= (currentHH.getDerivedHH()).getPerson(j+1);
                    current_page=currentPerson.getPAttr("AGE");
                    current_pESR=currentPerson.getPAttr("ESR");
                    
                    if(current_page>=0 && current_page<=4){
                        result[132][currentTAZ-1]++;
                    }
                    if(current_page>=5 && current_page<=19){
                        result[133][currentTAZ-1]++;
                    }
                    if(current_page>=20 && current_page<=44){
                        result[134][currentTAZ-1]++;
                    }
                    if(current_page>=45 && current_page<=64){
                        result[135][currentTAZ-1]++;
                    }
                    if(current_page>=65){
                        result[136][currentTAZ-1]++;
                    }
                    
                    //set universe 11-employed persons
                    if(current_pESR==1 || current_pESR==2 || current_pESR==4 || current_pESR==5){
                        result[137][currentTAZ-1]++;
                        
                        if (current_hunittype==0) {
                            result[138][currentTAZ-1]++;
                        }
                        if (current_hunittype>0) {
                            result[139][currentTAZ-1]++;
                        }
                    }
                }
            }            
		}
		
		return result;
	}
	
	//for testing purpose only
	//
	public static void main(String [] args){		
	}
}


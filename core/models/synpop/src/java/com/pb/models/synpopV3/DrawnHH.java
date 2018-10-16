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
 * Created on Apr 21, 2005
 * This class represents a HH object drawn into PopSyn
 */
package com.pb.models.synpopV3;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class DrawnHH {
	
	protected DerivedHH dhh;
	  //dimension 1 segment category, HHCat (316 in ARC)
	  protected int D1SCat;
	  protected int bucketBin;
	  protected int originalPUMA;
	  protected int selectedPUMA;
	  protected int taz;
	  protected int HHID;
	  
	public DrawnHH(DerivedHH dhh){
		this.dhh=dhh;
	}
	
	public int getHHAttr(String attr){
		if(attr.equalsIgnoreCase("D1SCat")){
			return D1SCat;
		}else if(attr.equalsIgnoreCase("bucketBin")){
			return bucketBin;
		}else if(attr.equalsIgnoreCase("originalPUMA")){
			return originalPUMA;
		}else if(attr.equalsIgnoreCase("selectedPUMA")){
			return selectedPUMA;
		}else if(attr.equalsIgnoreCase("TAZ")){
			return taz;
		}else if(attr.equalsIgnoreCase("HHID")){
			return HHID;
		}else{
			return dhh.getHHAttr(attr);
		}
	}
	
	public DerivedHH getDerivedHH(){
		return dhh;
	}
	
	public int getD1SCat(){
		return D1SCat;
	}
	
	public int getBucketBin(){
		return bucketBin;
	}
	
	public int getOriginalPUMA(){
		return originalPUMA;
	}
	
	public int getSelectedPUMA(){
		return selectedPUMA;
	}
	
	public int getTAZ(){
		return taz;
	}
	
	public int getHHID(){
		return HHID;
	}
	
	public void setD1SCat(int D1SCat){
		this.D1SCat=D1SCat;
	}
	
	public void setBucketBin(int bucketBin){
		this.bucketBin=bucketBin;
	}
	
	public void setOriginalPUMA(int originalPUMA){
		this.originalPUMA=originalPUMA;
	}
	
	public void setSelectedPUMA(int selectedPUMA){
		this.selectedPUMA=selectedPUMA;
	}
	
	public void setTAZ(int taz){
		this.taz=taz;
	}
	
	public void setHHID(int HHID){
		this.HHID=HHID;
	}

}

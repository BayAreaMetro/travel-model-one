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
package com.pb.models.synpopV3;

import java.util.Vector;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.0, Jan. 8, 2004
 */

public class PUMSBucketBin {

  //HHs in this bin (a vector of DerivedHH objects)
  protected Vector hhs;
  //number of HHs in this bin
  protected int NBinMembers;
  //times all HHs in this been has been drawn
  protected int NEmptied;


  public PUMSBucketBin() {
  	hhs=new Vector();
  }
  
  public void update(){
  	if(getNDrawn()==NBinMembers){
  		NEmptied++;
        //set drawn status of all HHs in this bin to "false"
    	setHHsDrawnSta(false);
  	}
  }
  
  public void reset(){
  	DerivedHH hh=null;
  	NEmptied=0;
  	for(int i=0; i<hhs.size();i++){
  		hh=(DerivedHH)hhs.get(i);
  		hh.reset();
  		hhs.set(i,hh);
  	}
  }
  
  public boolean isDone(){
	int NoEmptiedMax=new Integer(PropertyParser.getPropertyByName("NHHMax")).intValue();
    
	if (NEmptied== NoEmptiedMax||isEmpty()) return true;
    return false;
  }
    
  public boolean isEmpty(){
  	if(NBinMembers==0) return true;
  	return false;
  }

  public Vector getHHs(){
    return hhs;
  }

  /**
   * Get number of HHs in this bin which have been drawn.
   * @return
   */
  public int getNDrawn(){
    int result=0;
    DerivedHH tempHH;
    for(int i=0; i<hhs.size(); i++){
      tempHH=(DerivedHH)hhs.get(i);
      if(tempHH.getDrawnSta()){
        result++;
      }
    }
    return result;
  }

  public int getNEmptied(){
    return NEmptied;
  }

  public void increaseNEmptied(){
    NEmptied++;
  }

  public int getNBinMembers(){
    return NBinMembers;
  }

  /**
   * Add one HH to this bin.
   * @param hh represents a HH object.
   */
  public void addHH(DerivedHH hh){
    hhs.add(hh);
    NBinMembers++;
  }
  
  /**
   * set a DerivedHH to a position in hhs Vector
   * @param hhIndex
   * @param hh
   */
  public void setHH(int hhIndex,DerivedHH hh){
  	hhs.set(hhIndex,hh);
  }

  /**
   * Set drawn status of all HHs in this bin.
   * @param sta represents the drawn status to be set.
   */
  public void setHHsDrawnSta(boolean sta){
  	Vector updatedHHs=new Vector();
  	DerivedHH currentHH=null;
    for(int i=0; i<hhs.size(); i++){
      currentHH=((DerivedHH)hhs.get(i));
      currentHH.setDrawnSta(sta);
      updatedHHs.add(currentHH);
    }
    hhs=updatedHHs;
  }
}
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
import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, modified on Nov. 15, 2004
 * 
 * Represents attributes of PUMSHH, DerivedHH, PUMSPerson, and DerivedPerson.
 * Attributes are read in from property file.
 * 
 */

public class PUMSAttrs {
	
  protected static Logger logger;
  protected static Vector HHAttrs;
  protected static Vector DerivedHHAttrs;
  protected static Vector PersonAttrs;
  protected static Vector DerivedPersonAttrs;

  static {
    logger= Logger.getLogger("com.pb.models.synpopV3");
    HHAttrs=PropertyParser.getPropertyElementsByName("pums.hhattrs",",");
    DerivedHHAttrs=PropertyParser.getPropertyElementsByName("pums.derivedHHAttrs",",");
    PersonAttrs=PropertyParser.getPropertyElementsByName("pums.pattrs",",");
    DerivedPersonAttrs=PropertyParser.getPropertyElementsByName("pums.derivedPersonAttrs",",");
  }
  
  public static Vector getHHAttrs(){
    return HHAttrs;
  }

  public static Vector getPersonAttrs(){
    return PersonAttrs;
  }
  
  public static Vector getDerivedHHAttrs(){
  	return DerivedHHAttrs;
  }
  
  public static Vector getDerivedPersonAttrs(){
  	return DerivedPersonAttrs;
  }

  //for testing purpose only
  //successfully tested on March 23, 2005
  public static void main(String [] args){
  	Vector v1=PUMSAttrs.getHHAttrs();
  	Vector v2=PUMSAttrs.getPersonAttrs();
  	Vector v3=PUMSAttrs.getDerivedHHAttrs();
    System.out.println("ok, I am done");
  }
}
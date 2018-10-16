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
package com.pb.common.daf;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Iterator;

/** Defines a message. The class is abstract and must be extented to provide
 *  a "type". Message subclasses should call the protected constructor and
 *  provide the type of message.
 *
 * @author    Tim Heier
 * @version   1.0, 4/18/2002
 */
public abstract class Message implements Serializable {

    public static String REMOVE_MSG = "DAF_REMOVE_MSG";
    public static String RETURN_MSG = "DAF_RETURN_MSG";
    
    
    protected String Id;
    protected String sender;
    protected String recipient;
    protected MessageType mType;

    protected HashMap valueMap = new HashMap();

    private Message () {
    }

    protected Message (MessageType mType, String Id) {
        this.mType = mType;
        this.Id = Id;
    }

    public MessageType getType() {
        return mType;
    }

    public void setId( String Id ) {
        this.Id = Id;
    }

    public String getId() {
        return Id;
    }

    public void setSender( String sender ) {
        this.sender = sender;
    }

    public String getSender() {
        return sender;
    }

    public void setRecipient( String recipient ) {
        this.recipient = recipient;
    }

    public String getRecipient() {
        return recipient;
    }

    public void setValue( String keyName, Object value ) {
        valueMap.put( keyName, value );
    }

    public String getStringValue( String keyName ) {
        return (String)valueMap.get(keyName);
    }

    public void setStringValue( String keyName, String value ) {
        valueMap.put(keyName, (String)value );
    }

    public Object getValue( String keyName ) {
        return valueMap.get( keyName );
    }

    public HashMap getAllValues() {
        //Return a copy of the valueMap
        //HashMap copyOfMap = (HashMap)valueMap.clone();
        //return copyOfMap;
        return valueMap;
    }

    public void setAllValues(HashMap map) {
        valueMap = map;
    }

    public void setIntValue( String keyName, int intValue ) {
        valueMap.put( keyName, new Integer(intValue) );
    }

    public int getIntValue( String keyName ) {
        return ((Integer)valueMap.get(keyName)).intValue();
    }

    public void setFloatValue( String keyName, float floatValue ) {
        valueMap.put( keyName, new Float(floatValue) );
    }

    public float getFloatValue( String keyName ) {
        return ((Float)valueMap.get(keyName)).floatValue();
    }

    public void setDoubleValue( String keyName, double doubleValue ) {
        valueMap.put( keyName, new Double(doubleValue) );
    }

    public double getDoubleValue( String keyName ) {
        return ((Double)valueMap.get(keyName)).doubleValue();
    }

    public int getNumberOfValues() {
        return valueMap.size();
    }

    public Iterator valueIterator() {
        return valueMap.entrySet().iterator();
    }

    public void clearValues() {
        valueMap.clear();
    }

	public void setCoreNames(String keyName, String[] coreNames) {
		valueMap.put(keyName, coreNames);
	}

	public String[] getCoreNames(String keyName) {
		// TODO Auto-generated method stub
		return (String[]) valueMap.get(keyName);
	}

}

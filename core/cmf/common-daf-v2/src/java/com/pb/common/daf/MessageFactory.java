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

import org.apache.log4j.Logger;


/** A factory method implementation to create messages of different types.
 *
 * @author    Tim Heier
 * @version   1.0, 6/20/2002
 */
public class MessageFactory {
    static Logger logger = Logger.getLogger(MessageFactory.class);
    //Maintain a pools of messages to be recycled
    protected CompressedMessagePool compressedPool;
    protected UncompressedMessagePool uncompressedPool;

    private static MessageFactory instance = new MessageFactory();

    /** Keep this class from being created with "new".
     *
     */
    private MessageFactory() {
    }

    /** Return instances of this class.
     *
     */
    public static MessageFactory getInstance() {
        if(logger.isDebugEnabled()) logger.debug("Getting instance of MessageFactory");
        return instance;
    }

    /** Convienence method to return an uncompressed message.
     *
     */
    public Message createMessage() {
        return createMessage( false );
    }

    /** Factory method to create messages, compression can be specified
     * with a boolean flag.
     *
     */
    public Message createMessage(boolean compressMessage) {

        Message msg = null;

        if  (! compressMessage)  {
            msg = new UncompressedMessage( "empty_id" );
        }
        else {
            msg = new CompressedMessage( "empty_id" );
        }
        
        return msg;
    }

}
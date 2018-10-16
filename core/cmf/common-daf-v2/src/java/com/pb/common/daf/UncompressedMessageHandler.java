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

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.HashMap;

/** Handles reading and writing an uncompressed message.
 *
 * @author    Tim Heier
 * @version   1.0, 7/13/2002
 */
public class UncompressedMessageHandler extends MessageHandler {

    public UncompressedMessageHandler() {
    }


    /**
     * Write a message to an object output stream.
     *
     */
    protected void writedMessageBytes(Message msg, ObjectOutputStream oout) throws Exception {

        // Write each argument in order
        try {
            //Write message attributes
            oout.writeUTF( msg.Id );
            oout.writeUTF( msg.sender );
            oout.writeUTF( msg.recipient );

            //Write message arguments
            oout.writeObject( msg.getAllValues() );

        }
        catch (IOException e) {
            throw e;
        }
    }


    /**
     * Create and read a message from an object output stream.
     *
     */
    protected Message readMessageBytes( ObjectInputStream oin ) throws Exception {

        Message msg = MessageFactory.getInstance().createMessage();

        try {
            //Read message attributes
            msg.Id = (String) oin.readUTF();
            msg.sender = (String) oin.readUTF();
            msg.recipient = (String) oin.readUTF();

            //Read message arguments
            HashMap map = (HashMap) oin.readObject();
            msg.setAllValues( map ); 

        }
        catch (Exception e) {
            // Failed to read complete argument list or client closed connection.
            throw e;
        }

        return msg;
    }

}
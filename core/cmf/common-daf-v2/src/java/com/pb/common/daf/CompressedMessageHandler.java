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
import org.apache.log4j.Logger;
import java.util.zip.GZIPInputStream;

/** Handles reading and writing a compressed message.
 *
 * @author    Tim Heier
 * @version   1.0, 7/13/2002
 */
public class CompressedMessageHandler extends MessageHandler {

    protected Logger logger = Logger.getLogger("com.pb.common.daf");

    public static int BYTE_ARRAY_BUFFER = 64 * 1024;  //64K bytes to start with
    public static int ZIP_ARRAY_BUFFER  = 8 * 1024;   //8K bytes to start with

    //Streams for compression of argument list
    DAFByteArrayOutputStream bout = null;       //Reused between calls
    DAFGZIPOutputStream zout = null;            //Reused between calls
    ObjectOutputStream ooutBuffer = null;       //Reused between calls

    //Streams for de-compression of arguement list
    DAFByteArrayInputStream bin = null;         //Reused between calls
    GZIPInputStream zin = null;
    ObjectInputStream oinBuffer = null;

    public CompressedMessageHandler() {

        try {
            //Streams for compression of argument list
            bout = new DAFByteArrayOutputStream( BYTE_ARRAY_BUFFER );
            zout = new DAFGZIPOutputStream( bout  );
            ooutBuffer = new ObjectOutputStream( zout );
        }
        catch (Exception e) {
            logger.error("", e);
        }

    }


    /**
     * Write a message to an object output stream.
     *
     */
    protected void writedMessageBytes(Message msg, ObjectOutputStream oout) throws Exception {

        try {
            //Write message attributes
            oout.writeUTF( msg.Id );
            oout.writeUTF( msg.sender );
            oout.writeUTF( msg.recipient );

            //Compress arguements
            ooutBuffer.writeObject( msg.getAllValues() );

            // Finish with the end-of-message token
            ooutBuffer.writeObject( EndOfMessage.getInstance() );

            ooutBuffer.flush();  //flush object stream
            ooutBuffer.reset();  //Reset memory of objects stream has written
            zout.finish();       //finish compresseing bytes

            //Write message arguments to stream as compressed blob
            oout.writeObject( bout.getByteArray() );

            //Reset byte array count to 0
            bout.reset();
        }
        catch (IOException e) {
            throw e;
        }
    }


    /**
     * Create and read a message from an object output stream.
     *
     */
    protected Message readMessageBytes(ObjectInputStream oin) throws Exception {

        Message msg = MessageFactory.getInstance().createMessage( true );

        try {
            //Read message attributes
            msg.Id = (String) oin.readUTF();
            msg.sender = (String) oin.readUTF();
            msg.recipient = (String) oin.readUTF();

            //Read arguments as one compressed blob
            byte[] argbuf = (byte[]) oin.readObject();
            bin.setNewBuffer( argbuf );                //Reuse byte stream
            zin = new GZIPInputStream( bin );          //Create new a zip stream
            oinBuffer = new ObjectInputStream( zin );  //Create a new object stream

            //Read HashMap from compressed byte array
            HashMap map = (HashMap) oinBuffer.readObject();
            msg.setAllValues( map ); 
                        
        }
        catch (Exception e) {
            // Failed to read complete argument list or client closed connection.
            throw e;
        }

        return msg;
    }
}

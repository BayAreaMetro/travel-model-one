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
package com.pb.common.sql;

import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;

/**
 * Some helper methods.
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class SQLHelper {

    /**
     * Prints an arbitrary result set to the console. Useful for debugging.
     * 
     * @param rs
     */
    public static void printResultSet(ResultSet rs) {
        //Get the number of columns in result set
        ResultSetMetaData md;
        try {
            md = rs.getMetaData();
            int nCols = md.getColumnCount();
            int count = 0;
            
            //Print out the result set
            while (rs.next()) {
                
                for (int i=0; i < nCols; i++) {
                    String val = rs.getString(i+1);
                    if (i > 0)
                        System.out.print(", ");
                    System.out.print(val);
                }
                System.out.println();
                count++;
            }
            System.out.println(count + " rows were returned");

        } catch (SQLException e) {
            e.printStackTrace();
        }
        
    }
}

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

import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.apache.log4j.Logger;

/**
 * Represents a connection to a database.
 *
 * @author   Tim Heier
 * @version  1.0, 8/19/2000
 *
 */
public class JDBCConnection {
    
    protected static transient Logger logger = Logger.getLogger("com.pb.common.sql");
    
    private String  url;
    private String  driverName;
    private String  user;
    private String  passwd;

    private Connection  conn;
    private DatabaseMetaData  dbmd;
    private List tableNames = new ArrayList();


    /**
     * Create a connection to a database specified by the URL parameter.
     * 
     * @param url
     * @param driverName
     * @param user
     * @param passwd
     */
    public JDBCConnection(String url, String driverName, String user, String passwd) {
        this.url = url;
        this.driverName = driverName;
        this.setUser(user);
        this.setPasswd(passwd);

        logger.debug("JDBCConnection, URL: " + url);
        logger.debug("Driver Name: " + driverName);
        
        ResultSet tableNamesRS;

        Properties props = new Properties();
        props.setProperty("user", user);
        props.setProperty("password", passwd);
                
        try {
            Class.forName(driverName);
            conn = DriverManager.getConnection(url, props);
            
            dbmd = conn.getMetaData();
            ResultSet tableTypesRS = dbmd.getTableTypes();

            while (tableTypesRS.next()) {
               String tableType = tableTypesRS.getString("TABLE_TYPE");
            }

            /*This code works but we only need "table" and "view" table types.

            //getTables() wants list of types as an array not a vector
            int numberOfTableTypes = tabTypes.size();
            String[] tableTypes = new String[numberOfTableTypes];

            for (int i=0; i < numberOfTableTypes; i++) {
               tableTypes[i] = (String)tabTypes.elementAt(i);
            }
            */
            
            String[] tableTypes = {"table", "view"};
            
            //Get table names
            tableNamesRS = dbmd.getTables(null, null, "%", tableTypes);

            int i=0;
            while (tableNamesRS.next()) {
               String tabName = tableNamesRS.getString("TABLE_NAME");
               tableNames.add( tabName );
            }
        }
        catch (ClassNotFoundException e) {
            throw new RuntimeException("Cannot find the database driver classes.", e);
        }
        catch (SQLException e) {
            logger.fatal("Cannot connect to database "+url+" " + driverName);
            throw new RuntimeException("Cannot connect to database "+url+" " + driverName, e);
        }
    }

    
    /**
     * @return A list of the tables names in the database.
     */
    public String[] getTableNames() {
       String[] tables = new String[ tableNames.size() ];
       
       for (int i=0; i < tableNames.size(); i++) 
          tables[i] = (String) tableNames.get(i);
    	
       return tables;
    }


    /**
     * @return Returns a reference to the underlying JDBC connection.
     */
    public Connection getConnection() {
        return conn;
    }

    
    /**
     * @return Creates a JDBC statement.
     */
    public Statement createStatement() throws SQLException {
        return conn.createStatement();
    }

    
    /**
     * Closes this connection to the database.
     */
    public void close() {
        try {
            conn.close();
        }
        catch (SQLException e) {
            e.printStackTrace();
        }
    }

    /**
     * @return Returns the driverName.
     */
    public String getDriverName() {
        return driverName;
    }

    /**
     * @return Returns the url.
     */
    public String getUrl() {
        return url;
    }

    /**
     * @return Returns the user.
     */
    public String getUser() {
        return user;
    }


	private void setUser(String user) {
		this.user = user;
	}


	private void setPasswd(String passwd) {
		this.passwd = passwd;
	}


	private String getPasswd() {
		return passwd;
	}

}

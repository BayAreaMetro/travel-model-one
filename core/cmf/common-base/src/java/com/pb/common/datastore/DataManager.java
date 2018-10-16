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
package com.pb.common.datastore;

/**
 * The DataManager class provides functionallity for storing:
 *
 * 1. TableDataSet objects
 * 2. Java objects
 * 3. FileStreams
 *
 * @author    Tim Heier
 * @version   1.0, 8/16/2002
 *
 */

import com.borland.datastore.DataStore;
import com.borland.datastore.DataStoreConnection;
import com.borland.dx.dataset.StorageDataSet;
import com.borland.dx.dataset.TableDataSet;
import com.borland.dx.dataset.TextDataFile;
import com.pb.common.util.ResourceUtil;

import java.io.File;
import java.io.FileInputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ResourceBundle;


public class DataManager implements DataStoreManager, JDBCManager {

    //Class keys/values
    public static final String  STORE_NAME     = "DataStore.fileName";
    public static final String  STORE_USER     = "DataStore.userName";
    public static final String  STORE_PASSWORD = "DataStore.password";

    public static final String  PROPS_NAME     = "tlumip";

    //JDBC Type 4 driver names
    public static final String JDBC_DRIVER = "com.borland.datastore.jdbc.DataStoreDriver";
    public static final String JDBC_URL    = "jdbc:borland:dslocal:";

    private String storeName = "";
    private String dataStoreUrl = "";
    private String userName  = "";
    private String password  = "";

    private DataStoreConnection store = new DataStoreConnection();

    /**
     * Default constructor. Opens default data-store.  The default data-store
     * will be created if it does not exist.
     */
    public DataManager () {
        this("", "", "");
    }


    /**
     * Allows a named data-store to be opened.  A data-store will be created
     * if one does not exist.
     */
    public DataManager (String name, String user, String passwd) {

        //Load properties file if none are supplied
        if ((name == null) || (name.length() == 0 )) {
            loadProperties();
        }
        else {
            storeName = name;
            userName  = user;
            password  = passwd;
        }

        //Complete URL to the data-store
        dataStoreUrl = JDBC_URL + storeName;

        if ( !new File( storeName ).exists() )
            createStore( );

        openStore();

        //Load JDBC driver for DataStore
        try {
            Class.forName(JDBC_DRIVER);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }


    /**
     * Load application properties from an external Properties file.
     */
    private void loadProperties( ) {

        ResourceBundle rb = ResourceUtil.getResourceBundle( PROPS_NAME );

        storeName = ResourceUtil.getProperty(rb, STORE_NAME );
        userName  = ResourceUtil.getProperty(rb, STORE_USER );
        password  = ResourceUtil.getProperty(rb, STORE_PASSWORD );
    }


    public String getUserName() {
        return userName;
    }


    public String getPassword() {
        return password;
    }


    public String getURL() {
        return JDBC_URL + storeName;
    }


    /**
     * Create a new data-store object.
     */
    public void createStore( ) {

       System.out.println("Creating store: " + storeName);

       try {
            DataStore newStore = new DataStore();
            //TxManager txMan = new TxManager();
            //txMan.setRecordStatus( false );

            newStore.setFileName(storeName);
            newStore.setUserName(userName);
            //newStore.setTxManager(txMan);

            newStore.create();
            newStore.close();
        } catch ( Exception e ) {
            e.printStackTrace();
        }
    }


    /**
     * Opens a data-store.  Note: A data-store will be created if one
     * does not exist.
     */
    public void openStore( ) {

        //System.out.println("Opening store: " + storeName);

         store.setFileName(storeName);
         store.setUserName(userName);
         store.open();

    }


    /**
     * Close data-store object.
     */
    public synchronized void closeStore() {

            store.close();
    }


    /**
     * Add an object to the data-store.
     *
     * @param  name  Name of the object.
     * @param  obj   Reference to the object.
     */
    public synchronized void addObject(String name, Object obj) {

        String objName = "object/" + name;

        try {
            store.writeObject(objName, obj);
        }
        catch(Exception e) {
            e.printStackTrace();
        }
    }


    /**
     * Return an object from the data-store.
     *
     * @param  name  Name of the object.
     * @return obj   Reference to the requested object.
     */
    public synchronized Object getObject(String name) {

        String objName = "object/" + name;

        try {
            return (store.readObject( objName ));
        }
        catch(Exception e) {
            //Store not found generates an exception, return null instead.
        }

        return null;
    }


    /**
     * Get a TableDataSet object from the data-store. An empty table is
     * returned if the table does not exist.
     *
     * @param  tableName  Name of the table.
     */
    public synchronized TableDataSet getTableDataSet(String tableName) {

        TableDataSet table = new TableDataSet();

        try {
            table.setStoreName(tableName);
            table.setStore(store);
            table.open();
        } catch (com.borland.dx.dataset.DataSetException e) {
            e.printStackTrace();
        }

        return table;
    }


    /**
     * Close a TableDataSet.  This is a helper method (static)
     *
     * @param  table  Name of the table.
     */
    public static void closeTable(TableDataSet table) {

        try {
            table.close();
        } catch (com.borland.dx.dataset.DataSetException e) {
            e.printStackTrace();
        }
    }


    /**
     * Execute a JDBC query.
     *
     * @param  queryString  SQL to execute.
     */
    public synchronized ResultSet executeQuery (String queryString) {

        closeStore();

        Connection conn = createConnection();

        try {
            Statement stmt = conn.createStatement();
            stmt.executeQuery(queryString);
            return stmt.getResultSet();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
        finally {
            try {
                conn.close();
                openStore();
            }
            catch (Exception e) {
                e.printStackTrace();
            }
        }

        return null;
    }


    /**
     * Execute a JDBC update.
     *
     * @param   updateString  SQL to execute.
     * @return  bool true=no errors false=error
     */
    public synchronized boolean executeUpdate (String updateString) {

        closeStore();

        Connection conn = createConnection();

        try {
            Statement stmt = conn.createStatement();
            stmt.executeUpdate(updateString);
        }
        catch (Exception e) {
            e.printStackTrace();
            return false;
        }
        finally {
            try {
                conn.close();
                openStore();
            }
            catch (Exception e) {
                e.printStackTrace();
            }
        }
        return true;
    }


    /**
     * Opens a JDBC connection to the data-store.
     *
     * @return  Connection  A JDBC connection object.
     */
    private synchronized Connection createConnection() {

        Connection conn = null;
        try {
            conn = DriverManager.getConnection(dataStoreUrl, userName, password);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
        return conn;
    }


    /**
     * Checks if a file stream exists in the data-store.
     *
     */
    public boolean fileExists(String fileName) {

        boolean exists = false;

        try {
            exists = store.fileExists(fileName);
        }
        catch (Exception e) {
            e.printStackTrace();
        }

        return exists;
    }


    /**
     * Checks if a table stream exists in the data-store.
     *
     */
    public boolean tableExists(String tableName) {

        boolean exists = false;

        try {
            exists = store.tableExists(tableName);
        }
        catch (Exception e) {
            e.printStackTrace();
        }

        return exists;
    }


    /**
     * Deletes a table stream in the data-store.
     *
     */
    public void deleteTable(String tableName) {

        try {
            store.deleteStream(tableName);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }


    /**
     * Deletes a file stream in the data-store.
     *
     */
    public void deleteFile(String fileName) {

        deleteTable(fileName);
    }


    /**
     * Prints a directory of the data-store.
     *
     */
    public synchronized void printDirectory() {

        StorageDataSet storeDir;

        try {
            storeDir = store.openDirectory();
            while(storeDir.inBounds()) {
                short dirVal = storeDir.getShort(DataStore.DIR_TYPE);
                if ( (dirVal & DataStore.TABLE_STREAM) != 0 ) {
                    System.out.print( "T" );
                } else if ( (dirVal & DataStore.FILE_STREAM) != 0 ) {
                    System.out.print( "F" );
                } else {
                    System.out.print( "?" );
                }
                System.out.print(", ");

                System.out.print(storeDir.getString(DataStore.DIR_STORE_NAME));
                System.out.print(", ");

                int idVal = storeDir.getInt(DataStore.DIR_ID);
                System.out.print( new Integer(idVal) );
                System.out.print(", ");

                long lenVal = storeDir.getLong(DataStore.DIR_LENGTH);
                System.out.print( new Long(lenVal) );

                System.out.println();
                storeDir.next();
            }
            store.closeDirectory();
        } catch (com.borland.dx.dataset.DataSetException e) {
            e.printStackTrace();
        }
    }


    /**
     * Exports a table in the data-store to a text file.
     *
     * @param  tableName  Name of existing table in data-store.
     */
    public void exportTable(String tableName) {
        exportTable(tableName, tableName + ".csv");
    }


    /**
     * Exports a table in the data-store to a text file.
     *
     * @param  tableName  Name of existing table in data-store.
     * @param  fileName   Name of the new text file.
     */
    public void exportTable(String tableName, String fileName) {

        String fName = fileName;

        if (! fileName.endsWith(".csv")) {
            fName = fileName + ".csv";
        }

        try {
            TableDataSet table = getTableDataSet(tableName);

            TextDataFile tdf = new TextDataFile();
            tdf.setSeparator(",");
            tdf.setEncoding("ASCII");
            tdf.setFileName(fName);
            tdf.save(table);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }


    /**
     * Loads a table from a text file to a data-store.
     *
     * @param  tableName   Name of table to create in data-store.
     */
    public void loadTable(String tableName) {
        loadTable(tableName, tableName + ".csv", tableName + ".schema");
    }


    /**
     * Loads a table from a text file to a data-store.
     *
     * @param  tableName   Name of table to create in data-store.
     * @param  fileName    Name of the text file to load.
     */
    public void loadTable(String tableName, String fileName) {

        loadTable(tableName, fileName, fileName + ".schema");
    }


    /**
     * Loads a table from a text file to a data-store.
     *
     * @param  tableName   Name of table to create in data-store.
     * @param  fileName    Name of the text file to load.
     * @param  schemaName  Name of the schema file to load.
     */
    public void loadTable(String tableName, String fileName, String schemaName) {

        String fName = fileName;
        String sName = schemaName;

        if (! fileName.endsWith(".csv")) {
            fName = fileName + ".csv";
        }

        if (! schemaName.endsWith(".schema")) {
            sName = schemaName + ".schema";
        }

        try {
            FileInputStream dataStream = new FileInputStream(fName);
            FileInputStream schemaStream = new FileInputStream(sName);

            TextDataFile textdata = new TextDataFile();
            textdata.setLoadOnOpen(false);

            TableDataSet dataset = new TableDataSet();
            dataset.setDataFile(textdata);
            dataset.setStore(store);
            dataset.setStoreName(tableName);
            dataset.setTableName(tableName);

            dataset.open();
            textdata.load(dataset, dataStream, schemaStream);
            dataset.close();
        }
        catch(Exception e) {
            e.printStackTrace();
        }
    }

}

package com.pb.models.ctramp.sqlite;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;


public class SqliteService {

    Connection c = null;
    String databaseFile;
    
    public void connect( String fileName, String tableName ) throws DAOException {
        
        try {
            c = ConnectionHelper.getConnection( fileName );
            Statement s = c.createStatement();
            
            s.execute("CREATE TABLE IF NOT EXISTS " + tableName + " (" +
                    "   id INTEGER, " +
                    "   numProcessed INTEGER, " +
                    "   totalToProcess INTEGER, " +
                    "   startUp INTEGER, " +
                    "   runTime INTEGER, " +
                    "   shutDown INTEGER " +
                    ")" );

            s.execute("DELETE FROM " + tableName);
            

        } catch (SQLException e) {
            e.printStackTrace();
            throw new DAOException(e);
        }

    }

    
    public void listRecords( String tableName ) throws DAOException {

        try {
                    
            Statement s = c.createStatement();

            ResultSet rs = s.executeQuery("SELECT id, numProcessed, totalToProcess, startUp, runTime, shutDown FROM " + tableName + " ORDER BY id");
            while (rs.next()) {
                System.out.println( rs.getInt("id") + ", " + rs.getInt("numProcessed") + ", " + rs.getInt("totalToProcess") + ", " + rs.getInt("startUp") + ", " + rs.getInt("runTime") + ", " + rs.getInt("shutDown") );
            }

        } catch (SQLException e) {
            e.printStackTrace();
            throw new DAOException(e);
        }

    }

    
    public void insertRecord( String tableName, int id, int numProcessed, int totalToProcess, int startUp, int runTime, int shutDown) throws DAOException {

        try {
                    
            Statement s = c.createStatement();
            String query = String.format("INSERT INTO %s (id, numProcessed, totalToProcess, startUp, runTime, shutDown) VALUES (%d, %d, %d, %d, %d, %d)", tableName, id, numProcessed, totalToProcess, startUp, runTime, shutDown);
            s.execute( query );

        } catch (SQLException e) {
            e.printStackTrace();
            throw new DAOException(e);
        }

    }

    
    public void updateRecord( String tableName, int id, int numProcessed, int totalToProcess, int startUp, int runTime, int shutDown) throws DAOException {

        try {
                    
            Statement s = c.createStatement();
            String query = String.format("UPDATE %s SET numProcessed=%d, totalToProcess=%d, startUp=%d, runTime=%d, shutDown=%d WHERE id=%d", tableName, numProcessed, totalToProcess, startUp, runTime, shutDown, id);
            s.execute( query );

        } catch (SQLException e) {
            e.printStackTrace();
            throw new DAOException(e);
        }

    }

    
    public static void main(String[] args) {
        
        SqliteService s = new SqliteService();
        s.connect( "c:/jim/status.db", "uwsl" );
        
        s.insertRecord( "uwsl", 0, 27, 1250, 99, 102, 10 );
        s.insertRecord( "uwsl", 2, 29, 1250, 58, 101, 9 );
        s.insertRecord( "uwsl", 1, 32, 1250, 77, 99, 8 );
        s.listRecords( "uwsl" );

    }
    
}

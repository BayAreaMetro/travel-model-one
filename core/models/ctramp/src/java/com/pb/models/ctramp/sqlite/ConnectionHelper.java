package com.pb.models.ctramp.sqlite;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;


public class ConnectionHelper {

    private String url;
    private static ConnectionHelper instance;

    private ConnectionHelper( String fileName )
    {
        try {
            Class.forName( "org.sqlite.JDBC" );
            //url = "jdbc:sqlite:/c:/jim/projects/baylanta/data/status.db";
            url = "jdbc:sqlite:/" + fileName;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Connection getConnection( String fileName ) throws SQLException {
        if (instance == null) {
            instance = new ConnectionHelper( fileName );
        }
        try {
            return DriverManager.getConnection(instance.url);
        } catch (SQLException e) {
            throw e;
        }
    }
    
    public static void close(Connection connection)
    {
        try {
            if (connection != null) {
                connection.close();
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

}

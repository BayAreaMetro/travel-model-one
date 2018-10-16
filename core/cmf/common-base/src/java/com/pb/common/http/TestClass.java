package com.pb.common.http;

/**
 * Simple class to test ClassFileServer.
 */
public class TestClass implements Runnable {

    public void run() {
        System.out.println("hello from TestClass");
        Dependency d = new Dependency();
        d.printMessage();
    }
}

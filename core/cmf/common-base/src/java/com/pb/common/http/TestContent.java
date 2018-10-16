package com.pb.common.http;

import java.util.concurrent.Callable;

public class TestContent implements Callable<String> {

    public TestContent() {
    }

    public String call() throws Exception {
        System.out.println("Test Class in call() method");

        String response =
            "<html><body>\n" +
            "<h1>TestClass Page</h1><br/>\n" +
            "This is a response from a Java class...\n" +
            "</body></html>";

        return response;
    }
}


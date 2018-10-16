package com.pb.common.http;

import java.util.Properties;
import java.util.Enumeration;
import java.io.File;


public class HttpRequestProcessor {

    public static String START_HTML = "<html><body>";
    public static String END_HTML   = "</body></html>";
    public static String CR = "\n";
    public static String BR = "<br>" + "\n";

    public boolean showDebug = false;

    public HttpRequestProcessor() {
    }

    /**
     * Override this method to do your work. The return string should represent the entire
     * html for a page. See echoValues() method for an example.
     *
     * @param uri
     * @param method
     * @param header
     * @param params
     * @return
     */
    public String processRequest(File homeDir, String uri, String method, Properties header, Properties params) {

        return echoValues(homeDir, uri, method, header, params);
    }

    /**
     * Used by Web Server to pre-process parameters. Don't override this method unless it's
     * needed.
     *
     * @param homeDir
     * @param uri
     * @param method
     * @param header
     * @param params
     */
    public void PreProcessRequest(File homeDir, String uri, String method, Properties header, Properties params) {
        checkForDebug(params);
    }

    public void checkForDebug(Properties params) {
        String d = params.getProperty("debug");
        if ((d != null) && d.equalsIgnoreCase("true")) {
            showDebug = true;
        }
    }

    /**
     * Sample method to echo input values back to browser.
     *
     * @param uri
     * @param method
     * @param header
     * @param params
     * @return
     */
    public String echoValues(File homeDir, String uri, String method, Properties header, Properties params) {

        StringBuilder page = new StringBuilder(2048);
        page.append(START_HTML + CR);

        page.append("<h1>Echo</h1>" + CR);

        page.append("HomeDir = " + homeDir + BR);
        page.append("Uri = " + uri + BR);
        page.append("Method = " + method + BR);

        Enumeration e = header.propertyNames();
        while (e.hasMoreElements()) {
            String value = (String) e.nextElement();
            page.append("HDR: " + value + " = " + header.getProperty(value) + BR);
        }

        e = params.propertyNames();
        while (e.hasMoreElements()) {
            String value = (String) e.nextElement();
            page.append("PRM: " + value + " = " + params.getProperty(value) + BR);
        }

        page.append(END_HTML + CR);

        return page.toString();
    }
}

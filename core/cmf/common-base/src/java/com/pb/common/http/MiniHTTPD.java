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
package com.pb.common.http;

//import groovy.lang.Binding;
//import groovy.util.GroovyScriptEngine;

import com.pb.common.util.StackTraceUtil;

import java.io.*;
import java.util.*;
import java.util.concurrent.Callable;
import java.net.*;
import java.text.Format;
import java.text.SimpleDateFormat;

/**
 * A simple, tiny, nicely embeddable HTTP 1.0 server in Java
 * <p/>
 * <p> MiniHTTPD version 1.0,
 * <p/>
 * <p><b>Features & limitations: </b><ul>
 * <p/>
 * <li> Java 1.1 compatible </li>
 * <li> No fixed config files, logging, authorization etc. </li>
 * <li> Supports parameter parsing of GET and POST methods </li>
 * <li> Supports both dynamic content and file serving </li>
 * <li> Never caches anything </li>
 * <li> Doesn't limit bandwidth, request time or simultaneous connections </li>
 * <li> Default code serves files and shows all HTTP parameters and headers</li>
 * <li> File server supports directory listing, index.html and index.htm </li>
 * <li> File server does the 301 redirection trick for directories without '/'</li>
 * <li> File server supports simple skipping for files (continue download) </li>
 * <li> File server uses current directory as a web root </li>
 * <li> File server serves also very long files without memory overhead </li>
 * <li> Contains a built-in list of most common mime types </li>
 * <p/>
 * </ul>
 * <p/>
 * <p><b>Ways to use: </b><ul>
 * <p/>
 * <li> Run as a standalone app, serves files from current directory and shows requests</li>
 * <li> Subclass serve() and embed custom logic</li>
 * <li> Call serveFile() from serve() with your own base directory </li>
 * <p/>
 * </ul>
 */
public class MiniHTTPD {

    private boolean debug = false;
    private int httpPort;
    private String homeDir;

    //Format date to look like Log4j timestamp
    Format formatter = new SimpleDateFormat("dd-MMM-yyyy HH:mm:ss:SSS");
    
    /**
     * GMT date formatter
     */
    private static java.text.SimpleDateFormat gmtFrmt;

    static {
        gmtFrmt = new java.text.SimpleDateFormat("E, d MMM yyyy HH:mm:ss 'GMT'", Locale.US);
        gmtFrmt.setTimeZone(TimeZone.getTimeZone("GMT"));
    }

    /**
     * Hashtable mapping (String)FILENAME_EXTENSION -> (String)MIME_TYPE
     */
    private static Hashtable theMimeTypes = new Hashtable();

    static {
        StringTokenizer st = new StringTokenizer(
                        "htm        text/html " +
                        "html       text/html " +
                        "xml        text/plain " +
                        "txt        text/plain " +
                        "asc        text/plain " +
                        "log        text/plain " +
                        "cmd        text/plain " +
                        "sh         text/plain " +
                        "gif        image/gif " +
                        "jpg        image/jpeg " +
                        "jpeg       image/jpeg " +
                        "png        image/png " +
                        "mp3        audio/mpeg " +
                        "m3u        audio/mpeg-url " +
                        "pdf        application/pdf " +
                        "doc        application/msword " +
                        "ogg        application/x-ogg " +
                        "zip        application/octet-stream " +
                        "exe        application/octet-stream " +
                        "class      application/octet-stream ");
        while (st.hasMoreTokens())
            theMimeTypes.put(st.nextToken(), st.nextToken());
    }


    /**
     * Convenience constructor. Starts HTTP server on port 8080 and serves content
     * from the current working directory.<p>
     * 
     * Throws an IOException if the socket is already in use
     */
    public MiniHTTPD() throws IOException {
        this(8080, ".");
    }

    /**
     * Starts a HTTP server to given port.<p>
     * Throws an IOException if the socket is already in use
     */
    public MiniHTTPD(int port, String homeDir) throws IOException {
        this.httpPort = port;
        this.homeDir = homeDir;

        //Make sure homeDir is a directory
        File home = new File(homeDir);
        if (!home.isDirectory())
            throw new IOException("homeDir is not a directory " + home.getAbsolutePath());
       

        final ServerSocket ss = new ServerSocket(httpPort);
        Thread t = new Thread(new Runnable() {
            public void run() {
                try {
                    while (true)
                        new HTTPSession(ss.accept());
                }
                catch (IOException ioe) {
                }
            }
        });
        t.setDaemon(true);
        t.start();

        String currentDir = new File(".").getAbsolutePath();

        printMessage("MiniHTTPD listening on " + httpPort);
        printMessage("MiniHTTPD homeDir " + currentDir);

    }

    /**
     * Convenience method to print messages to the Server Log file and the console
     *
     * @param message
     */
    public void printMessage(String message) {

        //Add date/time to file entry
        String t = formatter.format(new Date());
        System.out.println(t + ", " + message);
    }

    public void setDebug(boolean debugValue) {
        this.debug = debugValue;
    }

    /**
     * Override this to customize the server.<p>
     * <p/>
     * (By default, this delegates to serveFile() and allows directory listing.)
     *
     * @return HTTP response, see class Response for details
     * @parm uri    Percent-decoded URI without parameters, for example "/index.cgi"
     * @parm method    "GET", "POST" etc.
     * @parm parms    Parsed, percent decoded parameters from URI and, in case of POST, data.
     * @parm header    Header entries, percent decoded
     */
    public Response serve(String uri, String method, Properties header, Properties params) {
        if (debug)
            System.out.println(method + " " + uri);

        //Print header and parameter values
        if (debug) {
            Enumeration e = header.propertyNames();
            while (e.hasMoreElements()) {
                String value = (String) e.nextElement();
                if (debug)
                    System.out.println("  HDR: " + value + " = " + header.getProperty(value));
            }
            e = params.propertyNames();
            while (e.hasMoreElements()) {
                String value = (String) e.nextElement();
                if (debug)
                    System.out.println("  PRM: " + value + " = " + params.getProperty(value));
            }
        }

        if (uri.endsWith("class")) {
            return serveClassFile(uri, method, header, params, new File(homeDir), true);
        }
//        else if (uri.endsWith("groovy")) {
//            return serveGroovyFile(uri, header, params, new File(homeDir), true);
//        }
        else {
            return serveFile(uri, method, header, params, new File(homeDir), true );
        }
    }

    /**
     * HTTP response.
     * Return one of these from serve().
     */
    class Response {
        /**
         * HTTP status code after processing, e.g. "200 OK", HTTP_OK
         */
        public String status;

        /**
         * MIME type of content, e.g. "text/html"
         */
        public String mimeType;

        /**
         * Data of the response, may be null.
         */
        public InputStream data;

        /**
         * Headers for the HTTP response. Use addHeader()
         * to add lines.
         */
        public Properties header = new Properties();
        /**
         * Default constructor: response = HTTP_OK, data = mime = 'null'
         */
        public Response() {
            this.status = HTTP_OK;
        }

        /**
         * Basic constructor.
         */
        public Response(String status, String mimeType, InputStream data) {
            this.status = status;
            this.mimeType = mimeType;
            this.data = data;
        }

        /**
         * Convenience method that makes an InputStream out of
         * given text.
         */
        public Response(String status, String mimeType, String txt) {
            this.status = status;
            this.mimeType = mimeType;
            this.data = new ByteArrayInputStream(txt.getBytes());
        }

        /**
         * Adds given line to the header.
         */
        public void addHeader(String name, String value) {
            header.put(name, value);
        }
    }

    /**
     * Some HTTP response status codes
     */
    public static final String
            HTTP_OK = "200 OK",
            HTTP_REDIRECT = "301 Moved Permanently",
            HTTP_FORBIDDEN = "403 Forbidden",
            HTTP_NOTFOUND = "404 Not Found",
            HTTP_BADREQUEST = "400 Bad Request",
            HTTP_INTERNALERROR = "500 Internal Server Error",
            HTTP_NOTIMPLEMENTED = "501 Not Implemented";

    /**
     * Common mime types for dynamic content
     */
    public static final String
            MIME_PLAINTEXT = "text/plain",
            MIME_HTML = "text/html",
            MIME_DEFAULT_BINARY = "application/octet-stream";

    /**
     * Handles one session, i.e. parses the HTTP request
     * and returns the response.
     */
    class HTTPSession implements Runnable {
        public HTTPSession(Socket s) {
            mySocket = s;
            Thread t = new Thread(this);
            t.setDaemon(true);
            t.start();
        }

        public void run() {
            try {
                InputStream is = mySocket.getInputStream();
                if (is == null) return;
                BufferedReader in = new BufferedReader(new InputStreamReader(is));

                // Read the request line
                StringTokenizer st = new StringTokenizer(in.readLine());
                if (!st.hasMoreTokens())
                    sendError(HTTP_BADREQUEST, "BAD REQUEST: Syntax error. Usage: GET /example/file.html");

                String method = st.nextToken();

                if (!st.hasMoreTokens())
                    sendError(HTTP_BADREQUEST, "BAD REQUEST: Missing URI. Usage: GET /example/file.html");

                String uri = decodePercent(st.nextToken());

                // Decode parameters from the URI
                Properties parms = new Properties();
                int qmi = uri.indexOf('?');
                if (qmi >= 0) {
                    decodeParms(uri.substring(qmi + 1), parms);
                    uri = decodePercent(uri.substring(0, qmi));
                }

                // If there's another token, it's protocol version,
                // followed by HTTP headers. Ignore version but parse headers.
                Properties header = new Properties();
                if (st.hasMoreTokens()) {
                    String line = in.readLine();
                    while (line.trim().length() > 0) {
                        int p = line.indexOf(':');
                        header.put(line.substring(0, p).trim(), line.substring(p + 1).trim());
                        line = in.readLine();
                    }
                }

                // If the method is POST, there may be parameters
                // in data section, too, read it:
                if (method.equalsIgnoreCase("POST")) {
                    long size = 0x7FFFFFFFFFFFFFFFl;
                    String contentLength = header.getProperty("Content-Length");
                    if (contentLength != null) {
                        try {
                            size = Integer.parseInt(contentLength);
                        }
                        catch (NumberFormatException ex) {
                        }
                    }
                    String postLine = "";
                    char buf[] = new char[512];
                    int read = in.read(buf);
                    while (read >= 0 && size > 0 && !postLine.endsWith("\r\n")) {
                        size -= read;
                        postLine += String.valueOf(buf);
                        if (size > 0)
                            read = in.read(buf);
                    }
                    postLine = postLine.trim();
                    decodeParms(postLine, parms);
                }

                // Ok, now do the serve()
                Response r = serve(uri, method, header, parms);
                if (r == null)
                    sendError(HTTP_INTERNALERROR, "SERVER INTERNAL ERROR: Serve() returned a null response.");
                else
                    sendResponse(r.status, r.mimeType, r.header, r.data);

                in.close();
            }
            catch (IOException ioe) {
                try {
                    sendError(HTTP_INTERNALERROR, "SERVER INTERNAL ERROR: IOException: " + ioe.getMessage());
                }
                catch (Throwable t) {
                }
            }
            catch (InterruptedException ie) {
                // Thrown by sendError, ignore and exit the thread.
            }
        }

        /**
         * Decodes the percent encoding scheme. <br/>
         * For example: "an+example%20string" -> "an example string"
         */
        private String decodePercent(String str) throws InterruptedException {
            try {
                StringBuffer sb = new StringBuffer();
                for (int i = 0; i < str.length(); i++) {
                    char c = str.charAt(i);
                    switch (c) {
                        case'+':
                            sb.append(' ');
                            break;
                        case'%':
                            sb.append((char) Integer.parseInt(str.substring(i + 1, i + 3), 16));
                            i += 2;
                            break;
                        default:
                            sb.append(c);
                            break;
                    }
                }
                return new String(sb.toString().getBytes());
            }
            catch (Exception e) {
                sendError(HTTP_BADREQUEST, "BAD REQUEST: Bad percent-encoding.");
                return null;
            }
        }

        /**
         * Decodes parameters in percent-encoded URI-format
         * ( e.g. "name=Jack%20Daniels&pass=Single%20Malt" ) and
         * adds them to given Properties.
         */
        private void decodeParms(String parms, Properties p)
                throws InterruptedException {
            if (parms == null)
                return;

            StringTokenizer st = new StringTokenizer(parms, "&");
            while (st.hasMoreTokens()) {
                String e = st.nextToken();
                int sep = e.indexOf('=');
                if (sep >= 0)
                    p.put(decodePercent(e.substring(0, sep)).trim(),
                            decodePercent(e.substring(sep + 1)));
            }
        }

        /**
         * Returns an error message as a HTTP response and
         * throws InterruptedException to stop furhter request processing.
         */
        private void sendError(String status, String msg) throws InterruptedException {
            sendResponse(status, MIME_PLAINTEXT, null, new ByteArrayInputStream(msg.getBytes()));
            throw new InterruptedException();
        }

        /**
         * Sends given response to the socket.
         */
        private void sendResponse(String status, String mime, Properties header, InputStream data) {
            try {
                if (status == null)
                    throw new Error("sendResponse(): Status can't be null.");

                OutputStream out = mySocket.getOutputStream();
                PrintWriter pw = new PrintWriter(out);
                pw.print("HTTP/1.0 " + status + " \r\n");

                if (mime != null)
                    pw.print("Content-Type: " + mime + "\r\n");

                if (header == null || header.getProperty("Date") == null)
                    pw.print("Date: " + gmtFrmt.format(new Date()) + "\r\n");

                if (header != null) {
                    Enumeration e = header.keys();
                    while (e.hasMoreElements()) {
                        String key = (String) e.nextElement();
                        String value = header.getProperty(key);
                        pw.print(key + ": " + value + "\r\n");
                    }
                }

                pw.print("\r\n");
                pw.flush();

                if (data != null) {
                    byte[] buff = new byte[2048];
                    while (true) {
                        int read = data.read(buff, 0, 2048);
                        if (read <= 0)
                            break;
                        out.write(buff, 0, read);
                    }
                }
                out.flush();
                out.close();
                if (data != null)
                    data.close();
            }
            catch (IOException ioe) {
                // Couldn't write? No can do.
                try {
                    mySocket.close();
                } catch (Throwable t) {
                }
            }
        }

        private Socket mySocket;
    }

    ;

    /**
     * URL-encodes everything between "/"-characters.
     * Encodes spaces as '%20' instead of '+'.
     */
    public static String encodeUri(String uri) {
        String newUri = "";
        StringTokenizer st = new StringTokenizer(uri, "/ ", true);
        while (st.hasMoreTokens()) {
            String tok = st.nextToken();
            if (tok.equals("/"))
                newUri += "/";
            else if (tok.equals(" "))
                newUri += "%20";
            else
                newUri += URLEncoder.encode(tok);
        }
        return newUri;
    }

    /**
     * Serves file from homeDir and its' subdirectories (only).
     * Uses only URI, ignores all headers and HTTP parameters.
     */
    public Response serveFile(String uri, String method, Properties header, Properties params,
                              File homeDir,
                              boolean allowDirectoryListing) {
        // Make sure we won't die of an exception later
        if (!homeDir.isDirectory())
            return new Response(HTTP_INTERNALERROR, MIME_PLAINTEXT,
                    "INTERNAL ERRROR: serveFile(): homeDir is not a directory " + homeDir.getAbsolutePath());

        // Remove URL arguments
        uri = uri.trim().replace(File.separatorChar, '/');
        if (uri.indexOf('?') >= 0)
            uri = uri.substring(0, uri.indexOf('?'));

        // Prohibit getting out of current directory
        if (uri.startsWith("..") || uri.endsWith("..") || uri.indexOf("../") >= 0)
            return new Response(HTTP_FORBIDDEN, MIME_PLAINTEXT,
                    "FORBIDDEN: Won't serve ../ for security reasons.");

        File f = new File(homeDir, uri);
        if (!f.exists())
            return new Response(HTTP_NOTFOUND, MIME_PLAINTEXT,
                    "Error 404, file not found.");

        // List the directory, if necessary
        if (f.isDirectory()) {
            // Browsers get confused without '/' after the
            // directory, send a redirect.
            if (!uri.endsWith("/")) {
                uri += "/";
                Response r = new Response(HTTP_REDIRECT, MIME_HTML,
                        "<html><body>Redirected: <a href=\"" + uri + "\">" +
                                uri + "</a></body></html>");
                r.addHeader("Location", uri);
                return r;
            }

            // First try index.html and index.htm
            if (new File(f, "index.html").exists())
                f = new File(homeDir, uri + "/index.html");
//            else if (new File(f, "index.htm").exists())
//                f = new File(homeDir, uri + "/index.htm");

            // No index file, list the directory
            else if (allowDirectoryListing) {
                String[] files = f.list();
                String msg = "<html><body><h1>Directory " + uri + "</h1><br/>";

                if (uri.length() > 1) {
                    String u = uri.substring(0, uri.length() - 1);
                    int slash = u.lastIndexOf('/');
                    if (slash >= 0 && slash < u.length())
                        msg += "<b><a href=\"" + uri.substring(0, slash + 1) + "\">..</a></b><br/>";
                }

                for (int i = 0; i < files.length; ++i) {
                    File curFile = new File(f, files[i]);
                    boolean dir = curFile.isDirectory();
                    if (dir) {
                        msg += "<b>";
                        files[i] += "/";
                    }

                    msg += "<a href=\"" + encodeUri(uri + files[i]) + "\">" +
                            files[i] + "</a>";

                    // Show file size
                    if (curFile.isFile()) {
                        long len = curFile.length();
                        msg += " &nbsp;<font size=2>(";
                        if (len < 1024)
                            msg += curFile.length() + " bytes";
                        else if (len < 1024 * 1024)
                            msg += curFile.length() / 1024 + "." + (curFile.length() % 1024 / 10 % 100) + " KB";
                        else
                            msg += curFile.length() / (1024 * 1024) + "." + curFile.length() % (1024 * 1024) / 10 % 100 + " MB";

                        msg += ")</font>";
                    }
                    msg += "<br/>";
                    if (dir) msg += "</b>";
                }
                return new Response(HTTP_OK, MIME_HTML, msg);
            } else {
                return new Response(HTTP_FORBIDDEN, MIME_PLAINTEXT,
                        "FORBIDDEN: No directory listing.");
            }
        }

        try {
            // Get MIME type from file name extension, if possible
            String mime = null;
            int dot = f.getCanonicalPath().lastIndexOf('.');
            if (dot >= 0)
                mime = (String) theMimeTypes.get(f.getCanonicalPath().substring(dot + 1).toLowerCase());
            if (mime == null)
                mime = MIME_DEFAULT_BINARY;

            // Support (simple) skipping:
            long startFrom = 0;
            String range = header.getProperty("Range");
            if (range != null) {
                if (range.startsWith("bytes=")) {
                    range = range.substring("bytes=".length());
                    int minus = range.indexOf('-');
                    if (minus > 0)
                        range = range.substring(0, minus);
                    try {
                        startFrom = Long.parseLong(range);
                    }
                    catch (NumberFormatException nfe) {
                    }
                }
            }

            FileInputStream fis = new FileInputStream(f);
            fis.skip(startFrom);
            Response r = new Response(HTTP_OK, mime, fis);
            r.addHeader("Content-length", "" + (f.length() - startFrom));
            r.addHeader("Content-range", "" + startFrom + "-" +
                    (f.length() - 1) + "/" + f.length());
            return r;
        }
        catch (IOException ioe) {
            return new Response(HTTP_FORBIDDEN, MIME_PLAINTEXT, "FORBIDDEN: Reading file failed.");
        }
    }

    public Response serveClassFile(String uri, String method, Properties header, Properties params,
                                   File homeDir, boolean allowDirectoryListing) {

        //replace "/" with system dependent file separator
        uri = uri.trim().replace(File.separatorChar, '/');
        File f = new File(homeDir, uri);
        int cIndex = f.getName().indexOf(".class");

        String className = f.getName().substring(0, cIndex);

        //make sure class file exists
//        if (!f.exists())
//            return new Response(HTTP_NOTFOUND, MIME_PLAINTEXT,
//                                "Error 404, file not found.");

        String responseText = "error processing request";
        try {
            Class cls = Class.forName(className);
            Object obj = cls.newInstance();

            if (obj instanceof HttpRequestProcessor) {
                responseText = ((HttpRequestProcessor) obj).processRequest(homeDir, uri, method, header, params);
            }
            else
            if (obj instanceof Callable) {
                responseText = (String) ((Callable) obj).call();
            }
            else {
                throw new Exception("Class must be instance of MiniHTTPD.Request or java.util.concurrent.Callable");
            }
        } catch (Exception e) {
            String msg = StackTraceUtil.getStackTrace(e);
            return new Response(HTTP_INTERNALERROR, MIME_PLAINTEXT, msg);
        }


        return new Response(HTTP_OK, MIME_HTML, responseText);
    }

//    public Response serveGroovyFile(String uri, Properties header, File homeDir,
//                                    boolean allowDirectoryListing) {
//
//        //replace "/" with system dependent file separator
//        uri = uri.trim().replace(File.separatorChar, '/');
//        File f = new File(homeDir, uri);
//        String dir = f.getParent();
//        String groovyFile = f.getName();
//
//        //make sure groovy file exists
//        if (!f.exists())
//            return new Response(HTTP_NOTFOUND, MIME_PLAINTEXT,
//                                "Error 404, file not found.");
//
//        //tch - this is for testing purposes
//        TestObject tobject = new TestObject();
//
//        //----- Set variables accessed by script
//        Binding binding = new Binding();
//        binding.setVariable("TestObject", tobject);
//
//        //----- ExecuteHandler script
//        String[] roots = new String[]{ dir };
//        GroovyScriptEngine gse = null;
//        try {
//            gse = new GroovyScriptEngine(roots);
//            gse.run( groovyFile , binding);
//        } catch (Exception e) {
//            return new Response(HTTP_INTERNALERROR, MIME_PLAINTEXT, e.toString() );
//        }
//
//        String responseText = (String) binding.getVariable("response");
//
//        return new Response(HTTP_OK, MIME_HTML, responseText);
//    }
//
//    //tch - used to test passing parameters to groovy file
//    public class TestObject {
//        public String testParam = "hello";
//        public HashMap testMap = new HashMap();
//
//        public TestObject () {
//            testMap.put("entry1", "value1");
//        }
//    }

    /**
     * Starts as a standalone file server and waits for Enter.
     */
    public static void main(String[] args) {
        System.out.println("MiniHTTPD 1.0 \n" + "Command line options: [port]  [home-dir]\n");

        // Change port if requested
        int port = 80;
        if (args.length >= 1) {
            port = Integer.parseInt(args[0]);
        }

        // Change port if requested
        String homeDir = new String(".");
        if (args.length >= 2) {
            homeDir = args[1];
        }

        MiniHTTPD server = null;
        try {
            server = new MiniHTTPD(port, homeDir);
        }
        catch (IOException ioe) {
            System.err.println("Couldn't start server:\n" + ioe);
            System.exit(-1);
        }

        System.out.println("Now serving files on port " + server.httpPort + " from \"" + server.homeDir + "\"");
        //new File("").getAbsolutePath() + "\"");
        System.out.println("Hit Enter to stop.\n");

        try {
            System.in.read();
        } catch (Throwable t) {
            
        }
    }

}

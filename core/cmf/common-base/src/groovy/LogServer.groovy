import groovy.net.xmlrpc.*
import java.net.ServerSocket

//Create LogServer
com.pb.common.logging.LogServer logger =
    new com.pb.common.logging.LogServer()

//For testing
echoFunction = { input ->
    println "input = " + input
    return input;
}

//Log method
logFunction = { message ->
    logger.log(message)
}

//Read log file and return contents as String
readLogFunction = {
    File logFile = new java.io.File(logger.clientLogName)
    text = logFile.getText()
    return text
}

clearLogFunction = {
    f = new FileWriter(logger.clientLogName, false)
    f.close()
}

//Create server and register methods
server = new XMLRPCServer()
server.echo = echoFunction
server.log = logFunction
server.viewLog = readLogFunction
server.clearLog = clearLogFunction

//Default port is 7002
serverSocket = new ServerSocket(logger.xmlRpcPort)
logger.printMessage("Xml-Rpc server listening on " + logger.xmlRpcPort)

server.startServer(serverSocket)

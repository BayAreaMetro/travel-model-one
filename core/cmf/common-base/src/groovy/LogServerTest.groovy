import groovy.net.xmlrpc.*

def serverProxy = new XMLRPCServerProxy("http://localhost:7002")

serverProxy.log("testing, testing")

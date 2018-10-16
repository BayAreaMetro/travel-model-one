/*
 * JPPF.
 * Copyright (C) 2005-2010 JPPF Team.
 * http://www.jppf.org
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jppf.server.node.remote;

import java.util.List;
import java.util.concurrent.Callable;

import org.jppf.JPPFNodeReconnectionNotification;
import org.jppf.classloader.*;
import org.jppf.comm.recovery.*;
import org.jppf.comm.socket.*;
import org.jppf.node.NodeRunner;
import org.jppf.server.node.JPPFNode;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * Instances of this class encapsulate execution nodes.
 * @author Laurent Cohen
 */
public class JPPFRemoteNode extends JPPFNode implements ClientConnectionListener
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(JPPFRemoteNode.class);
	/**
	 * Determines whether the debug level is enabled in the logging configuration, without the cost of a method call.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Connection to the revoery server.
	 */
	private ClientConnection clientConnection = null;

	/**
	 * Default constructor.
	 */
	public JPPFRemoteNode()
	{
		super();
	}

	/**
	 * Initialize this node's resources.
	 * @throws Exception if an error is raised during initialization.
	 * @see org.jppf.server.node.JPPFNode#initDataChannel()
	 */
	protected void initDataChannel() throws Exception
	{
		if (socketClient == null)
		{
			if (debugEnabled) log.debug("Initializing socket");
			TypedProperties props = JPPFConfiguration.getProperties();
			String host = props.getString("jppf.server.host", "localhost");
			int port = props.getInt("node.server.port", 11113);
			socketClient = new SocketClient();
			//socketClient = new SocketConnectorWrapper();
			socketClient.setHost(host);
			socketClient.setPort(port);
			socketClient.setSerializer(serializer);
			if (debugEnabled) log.debug("end socket client initialization");
			if (debugEnabled) log.debug("start socket initializer");
			System.out.println("Attempting connection to the node server at " + host + ":" + port);
			socketInitializer.initializeSocket(socketClient);
			if (!socketInitializer.isSuccessfull())
			{
				if (debugEnabled) log.debug("socket initializer failed");
				throw new JPPFNodeReconnectionNotification("Could not reconnect to the driver");
			}
			System.out.println("Reconnected to the node server");
			if (debugEnabled) log.debug("end socket initializer");
		}
		nodeIO = new RemoteNodeIO(this);
		if (JPPFConfiguration.getProperties().getBoolean("jppf.recovery.enabled", true))
		{
			if (clientConnection == null)
			{
				if (debugEnabled) log.debug("Initializing recovery");
				clientConnection = new ClientConnection(uuid);
				clientConnection.addClientConnectionListener(this);
				new Thread(clientConnection, "reaper client connection").start();
			}
		}
	}

	/**
	 * Initialize this node's data channel.
	 * @throws Exception if an error is raised during initialization.
	 * @see org.jppf.server.node.JPPFNode#closeDataChannel()
	 */
	protected void closeDataChannel() throws Exception
	{
		if (debugEnabled) log.debug("closing data channel: socketClient=" + socketClient + ", clientConnection=" + clientConnection);
		if (socketClient != null)
		{
			SocketWrapper tmp = socketClient;
			socketClient = null;
			tmp.close();
		}
		if (clientConnection != null)
		{
			//clientConnection.removeClientConnectionListener(this);
			ClientConnection tmp = clientConnection;
			clientConnection = null;
			tmp.close();
		}
	}

	/**
	 * Create the class loader for this node.
	 * @return a {@link JPPFClassLoader} instance.
	 */
	protected AbstractJPPFClassLoader createClassLoader()
	{
		if (debugEnabled) log.debug("Initializing classloader");
		if (classLoader == null) classLoader = NodeRunner.getJPPFClassLoader();
		return classLoader;
	}

	/**
	 * Instantiate the callback used to create the class loader in each {@link JPPFRemoteContainer}.
	 * @param uuidPath the uuid path containing the key to the container.
	 * @return a {@link Callable} instance.
	 */
	protected Callable<AbstractJPPFClassLoader> newClassLoaderCreator(final List<String> uuidPath)
	{
		return new Callable<AbstractJPPFClassLoader>()
		{
			public AbstractJPPFClassLoader call()
			{
				return new JPPFClassLoader(getClassLoader(), uuidPath);
			}
		};
	}

	/**
	 * {@inheritDoc}
	 */
	protected JPPFRemoteContainer newJPPFContainer(List<String> uuidPath, AbstractJPPFClassLoader cl) throws Exception
	{
		return new JPPFRemoteContainer(socketClient, uuidPath, cl);
	}

	/**
	 * {@inheritDoc}
	 */
	public void clientConnectionFailed(ClientConnectionEvent event)
	{
		try
		{
			if (debugEnabled) log.debug("recovery connection failed, attempting to reconnect this node");
			closeDataChannel();
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
		}
	}
}

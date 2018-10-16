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

package org.jppf.client;

import static org.jppf.client.JPPFClientConnectionStatus.FAILED;

import java.util.*;
import java.util.concurrent.locks.ReentrantLock;

import org.jppf.JPPFError;
import org.jppf.client.event.*;
import org.jppf.comm.discovery.JPPFConnectionInformation;
import org.jppf.comm.socket.*;
import org.jppf.management.JMXDriverConnectionWrapper;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * This class provides an API to submit execution requests and administration
 * commands, and request server information data.<br>
 * It has its own unique identifier, used by the nodes, to determine whether
 * classes from the submitting application should be dynamically reloaded or not
 * depending on whether the uuid has changed or not.
 * @author Laurent Cohen
 */
public class JPPFClientConnectionImpl extends AbstractJPPFClientConnection
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(JPPFClientConnectionImpl.class);
	/**
	 * Determines whether debug-level logging is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Used to synchronize request submissions performed by mutliple threads.
	 */
	private ReentrantLock lock = new ReentrantLock();
	/**
	 * Provides access to the management functions of the driver.
	 */
	private JMXDriverConnectionWrapper jmxConnection = null;
	/**
	 * 
	 */
	private int jmxPort = -1;
	/**
	 * Contains the configuration properties for this client connection.
	 */
	private TypedProperties props = null;

	/**
	 * Initialize this client with a specified application UUID.
	 * @param client the JPPF client that owns this connection.
	 * @param uuid the unique identifier for this local client.
	 * @param name configuration name for this local client.
	 * @param info the connection properties for this connection.
	 */
	public JPPFClientConnectionImpl(JPPFClient client, String uuid, String name, JPPFConnectionInformation info)
	{
		this.client = client;
		classServerPort = info.classServerPorts[0];
		jmxPort = info.managementPort;
		//configure(uuid, name + " (" + info.host + ":" + info.managementPort + ")", info.host, info.applicationServerPorts[0], classServerPort, 0);
		configure(uuid, name, info.host, info.applicationServerPorts[0], classServerPort, 0);
		initializeJmxConnection();
	}

	/**
	 * Initialize this client connection.
	 * @see org.jppf.client.JPPFClientConnection#init()
	 */
	public void init()
	{
		try
		{
			delegate = new ClassServerDelegateImpl(this, appUuid, host, classServerPort);
			delegate.addClientConnectionStatusListener(new ClientConnectionStatusListener()
			{
				public void statusChanged(ClientConnectionStatusEvent event)
				{
					delegateStatusChanged(event);
				}
			});
			taskServerConnection.addClientConnectionStatusListener(new ClientConnectionStatusListener()
			{
				public void statusChanged(ClientConnectionStatusEvent event)
				{
					taskServerConnectionStatusChanged(event);
				}
			});
			delegate.init();
			initCredentials();
			if (!delegate.isClosed())
			{
				Thread t = new Thread(delegate);
				t.setName("[" + delegate.getName() + " : class delegate]");
				t.start();
				taskServerConnection.init();
				//setStatus(delegate.getStatus());
			}
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
			setStatus(FAILED);
		}
		catch(JPPFError e)
		{
			setStatus(FAILED);
			throw e;
		}
	}

	/**
	 * Initialize the jmx connection using the specifed jmx server id.
	 */
	public void initializeJmxConnection()
	{
		String mHost = null;
		int port = -1;
		if (props != null)
		{
			String prefix = name + ".";
			mHost = props.getString(prefix + "jppf.management.host", "localhost");
			port = props.getInt(prefix + "jppf.management.port", 11198);
		}
		else
		{
			if (jmxPort < 0) return;
			mHost = host;
			port = jmxPort;
		}
		mHost = NetworkUtils.getHostName(mHost);
		jmxConnection = new JMXDriverConnectionWrapper(mHost, port);
		jmxConnection.connect();
	}

	/**
	 * Submit the request to the server.
	 * @param job the job to execute remotely.
	 * @throws Exception if an error occurs while sending the request.
	 * @see org.jppf.client.JPPFClientConnection#submit(org.jppf.client.JPPFJob)
	 */
	public void submit(JPPFJob job) throws Exception
	{
		AsynchronousResultProcessor proc = new AsynchronousResultProcessor(this, job);
		executor.submit(proc);
		if (debugEnabled) log.debug("["+name+"] submitted " + job.getTasks().size() + " tasks");
	}

	/**
	 * Shutdown this client and retrieve all pending executions for resubmission.
	 * @return a list of <code>JPPFJob</code> instances to resubmit.
	 * @see org.jppf.client.JPPFClientConnection#close()
	 */
	public List<JPPFJob> close()
	{
		if (!isShutdown)
		{
			isShutdown = true;
			try
			{
				if (taskServerConnection != null) taskServerConnection.close();
				if (delegate != null) delegate.close();
				if (jmxConnection != null) jmxConnection.close();
			}
			catch(Exception e)
			{
				if (debugEnabled) log.debug("[" + name + "] "+ e.getMessage(), e);
				else log.error("[" + name + "] "+ e.getMessage());
			}
			List<Runnable> pending = new ArrayList<Runnable>();
			pending.addAll(executor.shutdownNow());
			List<JPPFJob> result = new ArrayList<JPPFJob>();
			if (job != null) result.add(job);
			while (!pending.isEmpty())
			{
				AsynchronousResultProcessor proc = (AsynchronousResultProcessor) pending.remove(0);
				result.add(proc.getJob());
			}
			return result;
		}
		return null;
	}

	/**
	 * Create a socket initializer.
	 * @return an instance of <code>SocketInitializerImpl</code>.
	 * @see org.jppf.client.AbstractJPPFClientConnection#createSocketInitializer()
	 */
	protected SocketInitializer createSocketInitializer()
	{
		return new SocketInitializerImpl();
	}

	/**
	 * Get the lock used to synchronize request submissions performed by mutliple threads.
	 * @return  a <code>ReentrantLock</code> instance.
	 */
	public ReentrantLock getLock()
	{
		return lock;
	}

	/**
	 * Get the object that provides access to the management functions of the driver.
	 * @return a <code>JMXConnectionWrapper</code> instance.
	 */
	public JMXDriverConnectionWrapper getJmxConnection()
	{
		return jmxConnection;
	}
}

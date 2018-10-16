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
package org.jppf.server;

import java.util.*;

import org.jppf.JPPFException;
import org.jppf.classloader.LocalClassLoaderChannel;
import org.jppf.comm.discovery.*;
import org.jppf.comm.recovery.RecoveryServer;
import org.jppf.logging.jmx.JmxMessageNotifier;
import org.jppf.management.*;
import org.jppf.process.LauncherListener;
import org.jppf.security.JPPFSecurityContext;
import org.jppf.server.app.JPPFApplicationServer;
import org.jppf.server.job.JPPFJobManager;
import org.jppf.server.nio.ChannelWrapper;
import org.jppf.server.nio.classloader.*;
import org.jppf.server.nio.nodeserver.*;
import org.jppf.server.node.local.JPPFLocalNode;
import org.jppf.server.peer.*;
import org.jppf.server.queue.*;
import org.jppf.server.scheduler.bundle.Bundler;
import org.jppf.server.scheduler.bundle.spi.JPPFBundlerFactory;
import org.jppf.startup.*;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * This class serves as an initializer for the entire JPPF server. It follows the singleton pattern and provides access,
 * accross the JVM, to the tasks execution queue.
 * <p>It also holds a server for incoming client connections, a server for incoming node connections, along with a class server
 * to handle requests to and from remote class loaders. 
 * @author Laurent Cohen
 */
public class JPPFDriver
{
	/**
	 * Logger for this class.
	 */
	static Logger log = LoggerFactory.getLogger(JPPFDriver.class);
	/**
	 * Determines whether debug-level logging is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Singleton instance of the JPPFDriver.
	 */
	private static JPPFDriver instance = null;
	/**
	 * The queue that handles the tasks to execute. Objects are added to, and removed from, this queue, asynchronously and by
	 * multiple threads.
	 */
	private JPPFQueue taskQueue = null;
	/**
	 * Serves the execution requests coming from client applications.
	 */
	private JPPFApplicationServer[] applicationServers = null;
	/**
	 * Serves the JPPF nodes.
	 */
	private NodeNioServer nodeNioServer = null;
	/**
	 * Serves class loading requests from the JPPF nodes.
	 */
	private ClassNioServer classServer = null;
	/**
	 * Determines whether this server has initiated a shutdown, in which case it does not accept connections anymore.
	 */
	private boolean shuttingDown = false;
	/**
	 * Security credentials associated with this JPPF driver.
	 */
	private JPPFSecurityContext credentials = null;
	/**
	 * The jmx server used to manage and monitor this driver.
	 */
	private JMXServerImpl jmxServer = null;
	/**
	 * A list of objects containing the information required to connect to the nodes JMX servers.
	 */
	private Map<ChannelWrapper<?>, JPPFManagementInfo> nodeInfo = new HashMap<ChannelWrapper<?>, JPPFManagementInfo>();
	/**
	 * The thread that performs the peer servers discovery.
	 */
	private PeerDiscoveryThread peerDiscoveryThread = null;
	/**
	 * This listener gathers the statistics published through the management interface.
	 */
	private JPPFDriverStatsUpdater statsUpdater = new JPPFDriverStatsUpdater();
	/**
	 * Generates the statistcs events of which all related listeners are notified.
	 */
	private JPPFDriverStatsManager statsManager = new JPPFDriverStatsManager();
	/**
	 * Manages and monitors the jobs thoughout their processing within this driver.
	 */
	private JPPFJobManager jobManager = null;
	/**
	 * Uuid for this driver.
	 */
	private String uuid = new JPPFUuid().toString();
	/**
	 * The thread that broadcasts the server connection information using UDP multicast.
	 */
	private JPPFBroadcaster broadcaster = null;
	/**
	 * The server used to detect that individual connections are broken due to hardware failures.
	 */
	private RecoveryServer recoveryServer = null;

	/**
	 * Initialize this JPPFDriver.
	 */
	protected JPPFDriver()
	{
		// initialize the jmx logger
		new JmxMessageNotifier();
		statsManager.addListener(statsUpdater);
		credentials = new DriverInitializer(this).initCredentials();
		if (debugEnabled) log.debug("instantiating JPPF driver with uuid=" + uuid);
	}

	/**
	 * Initialize and start this driver.
	 * @throws Exception if the initialization fails.
	 */
	public void run() throws Exception
	{
		DriverInitializer init = new DriverInitializer(this);
		jobManager = new JPPFJobManager();
		taskQueue = new JPPFPriorityQueue();
		((JPPFPriorityQueue) taskQueue).addQueueListener(jobManager);
		JPPFConnectionInformation info = init.createConnectionInformation();
		TypedProperties config = JPPFConfiguration.getProperties();

		if (config.getBoolean("jppf.recovery.enabled", true))
		{
			recoveryServer = new RecoveryServer();
			new Thread(recoveryServer, "RecoveryServer thread").start();
		}

		classServer = new ClassNioServer(info.classServerPorts);
		classServer.start();
		init.printInitializedMessage(info.classServerPorts, "Class Server");

		applicationServers = new JPPFApplicationServer[info.applicationServerPorts.length];
		for (int i=0; i<info.applicationServerPorts.length; i++)
		{
			applicationServers[i] = new JPPFApplicationServer(info.applicationServerPorts[i]);
			applicationServers[i].start();
		}
		init.printInitializedMessage(info.applicationServerPorts, "Client Server");

		nodeNioServer = new NodeNioServer(info.nodeServerPorts);
		nodeNioServer.start();
		init.printInitializedMessage(info.nodeServerPorts, "Tasks Server");

		if (config.getBoolean("jppf.local.node.enabled", false))
		{
			LocalClassLoaderChannel localClassChannel = new LocalClassLoaderChannel(new LocalClassContext());
			LocalNodeChannel localNodeChannel = new LocalNodeChannel(new LocalNodeContext());
			JPPFLocalNode node = new JPPFLocalNode(localNodeChannel, localClassChannel);
			classServer.initLocalChannel(localClassChannel);
			nodeNioServer.initLocalChannel(localNodeChannel);
			new Thread(node, "Local node").start();
		}
		
		try
		{
			if (config.getBoolean("jppf.management.enabled", true))
			{
				jmxServer = new JMXServerImpl(JPPFAdminMBean.DRIVER_SUFFIX);
				jmxServer.start(getClass().getClassLoader());
				info.managementPort = JPPFConfiguration.getProperties().getInt("jppf.management.port", 11198);
				init.registerProviderMBeans();
				System.out.println("JPPF Driver management initialized");
			}
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
			config.setProperty("jppf.management.enabled", "false");
			String s = e.getMessage();
			s = (s == null) ? "<none>" : s.replace("\t", "  ").replace("\n", " - ");
			System.out.println("JPPF Driver management failed to initialize, with error message: '" + s + "'");
			System.out.println("Management features are disabled. Please consult the driver's log file for more information");
		}
		new JPPFStartupLoader<JPPFDriverStartupSPI>().load(JPPFDriverStartupSPI.class);

		if (config.getBoolean("jppf.discovery.enabled", true))
		{
			broadcaster = new JPPFBroadcaster(info);
			new Thread(broadcaster, "JPPF Broadcaster").start();
		}
		initPeers();
		System.out.println("JPPF Driver initialization complete");
	}

	/**
	 * Initialize this driver's peers.
	 */
	private void initPeers()
	{
		TypedProperties props = JPPFConfiguration.getProperties();
		if (props.getBoolean("jppf.peer.discovery.enabled", false))
		{
			if (debugEnabled) log.debug("starting peers discovery");
			peerDiscoveryThread = new PeerDiscoveryThread();
			new Thread(peerDiscoveryThread).start();
		}
		else
		{
			String peerNames = props.getString("jppf.peers");
			if ((peerNames == null) || "".equals(peerNames.trim())) return;
			if (debugEnabled) log.debug("found peers in the configuration");
			String[] names = peerNames.split("\\s");
			for (String peerName: names) new JPPFPeerInitializer(peerName).start();
		}
	}
	
	/**
	 * Get the singleton instance of the JPPFDriver.
	 * @return a <code>JPPFDriver</code> instance.
	 */
	public static JPPFDriver getInstance()
	{
		//if (instance == null) instance = new JPPFDriver();
		return instance;
	}

	/**
	 * Get the queue that handles the tasks to execute.
	 * @return a JPPFQueue instance.
	 */
	public static JPPFQueue getQueue()
	{
		return getInstance().taskQueue;
	}
	
	/**
	 * Get the JPPF class server.
	 * @return a <code>ClassNioServer</code> instance.
	 */
	public ClassNioServer getClassServer()
	{
		return classServer;
	}

	/**
	 * Get the JPPF nodes server.
	 * @return a <code>NodeNioServer</code> instance.
	 */
	public NodeNioServer getNodeNioServer()
	{
		return nodeNioServer;
	}

	/**
	 * Get the jmx server used to manage and monitor this driver.
	 * @return a <code>JMXServerImpl</code> instance.
	 */
	public synchronized JMXServerImpl getJmxServer()
	{
		return jmxServer;
	}

	/**
	 * Get the thread that performs the peer servers discovery.
	 * @return a <code>PeerDiscoveryThread</code> instance.
	 */
	public PeerDiscoveryThread getPeerDiscoveryThread()
	{
		return peerDiscoveryThread;
	}

	/**
	 * Determines whether this server has initiated a shutdown, in which case it does not accept connections anymore.
	 * @return true if a shutdown is initiated, false otherwise.
	 */
	public boolean isShuttingDown()
	{
		return shuttingDown;
	}

	/**
	 * Get the security credentials associated with this JPPF driver.
	 * @return a <code>JPPFSecurityContext</code> instance.
	 */
	public JPPFSecurityContext getCredentials()
	{
		return credentials;
	}

	/**
	 * Get this driver's unique identifier.
	 * @return the uuid as a string.
	 */
	public String getUuid()
	{
		return uuid;
	}

	/**
	 * Initialize this task with the specified parameters.<br>
	 * The shutdown is initiated after the specified shutdown delay has expired.<br>
	 * If the restart parameter is set to false then the JVM exits after the shutdown is complete.
	 * @param shutdownDelay delay, in milliseconds, after which the server shutdown is initiated. A value of 0 or less
	 * means an immediate shutdown.
	 * @param restart determines whether the server should restart after shutdown is complete.
	 * If set to false, then the JVM will exit.
	 * @param restartDelay delay, starting from shutdown completion, after which the server is restarted.
	 * A value of 0 or less means the server is restarted immediately after the shutdown is complete. 
	 */
	public void initiateShutdownRestart(long shutdownDelay, boolean restart, long restartDelay)
	{
		log.info("Scheduling server shutdown in " + shutdownDelay + " ms");
		shuttingDown = true;
		if (shutdownDelay <= 0L) shutdownDelay = 0L;
		Timer timer = new Timer();
		ShutdownRestartTask task = new ShutdownRestartTask(timer, restart, restartDelay);
		timer.schedule(task, shutdownDelay);
	}
	
	/**
	 * Shutdown this server and all its components.
	 */
	public void shutdown()
	{
		log.info("Shutting down");
		if (broadcaster != null)
		{
			broadcaster.setStopped(true);
			broadcaster = null;
		}
		if (peerDiscoveryThread != null)
		{
			peerDiscoveryThread.setStopped(true);
			peerDiscoveryThread = null;
		}
		classServer.end();
		classServer = null;
		if (nodeNioServer != null)
		{
			nodeNioServer.end();
			nodeNioServer = null;
		}
		for (int i=0; i<applicationServers.length; i++)
		{
			applicationServers[i].end();
			applicationServers[i] = null;
		}
		applicationServers = null;
		try
		{
			if (getJmxServer() != null) getJmxServer().stop();
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
		}
		jobManager.close();
	}

	/**
	 * Add a node information object to the map of node information.
	 * @param channel a <code>SocketChannel</code> instance.
	 * @param info a <code>JPPFNodeManagementInformation</code> instance.
	 */
	public void addNodeInformation(ChannelWrapper<?> channel, JPPFManagementInfo info)
	{
		synchronized (nodeInfo)
		{
			nodeInfo.put(channel, info);
		}
	}

	/**
	 * Remove a node information object from the map of node information.
	 * @param channel a <code>SocketChannel</code> instance.
	 */
	public void removeNodeInformation(ChannelWrapper channel)
	{
		synchronized (nodeInfo)
		{
			nodeInfo.remove(channel);
		}
	}

	/**
	 * Remove a node information object from the map of node information.
	 * @return channel a <code>SocketChannel</code> instance.
	 */
	public Map<ChannelWrapper<?>, JPPFManagementInfo> getNodeInformationMap()
	{
		synchronized (nodeInfo)
		{
			return Collections.unmodifiableMap(nodeInfo);
		}
	}

	/**
	 * Get the system information for the specified node.
	 * @param channel the node for which ot get the information.
	 * @return a <code>NodeManagementInfo</code> instance, or null if no informaiton is recorded for the node.
	 */
	public JPPFManagementInfo getNodeInformation(ChannelWrapper channel)
	{
		synchronized (nodeInfo)
		{
			return nodeInfo.get(channel);
		}
	}

	/**
	 * Get the listener that gathers the statistics published through the management interface.
	 * @return a <code>JPPFStatsUpdater</code> instance.
	 */
	public JPPFDriverStatsUpdater getStatsUpdater()
	{
		return statsUpdater;
	}

	/**
	 * Get a reference to the object that generates the statistics events of which all related listeners are notified.
	 * @return a <code>JPPFDriverStatsManager</code> instance.
	 */
	public JPPFDriverStatsManager getStatsManager()
	{
		return statsManager;
	}

	/**
	 * Get the object that manages and monitors the jobs thoughout their processing within this driver.
	 * @return an instance of <code>JPPFJobManager</code>.
	 */
	public JPPFJobManager getJobManager()
	{
		return jobManager;
	}

	/**
	 * Get the bundle factory used by the node server.
	 * @return a <code>JPPFBundlerFactory</code> instance.
	 */
	public JPPFBundlerFactory getBundlerFactory()
	{
		return nodeNioServer.getBundlerFactory();
	}

	/**
	 * Set the bundler used by the node server.
	 * @param bundler a <code>Bundler</code> instance.
	 */
	public void setBundler(Bundler bundler)
	{
		nodeNioServer.setBundler(bundler);
	}

	/**
	 * Start the JPPF server.
	 * @param args not used.
	 */
	public static void main(String...args)
	{
		try
		{
			if (debugEnabled) log.debug("starting the JPPF driver");
			if ((args == null) || (args.length <= 0))
			{
				throw new JPPFException("The driver should be run with an argument representing a valid TCP port or 'noLauncher'");
			}
			if (!"noLauncher".equals(args[0]))
			{
				int port = Integer.parseInt(args[0]);
				new LauncherListener(port).start();
			}

			instance = new JPPFDriver();
			instance.run();
			//JPPFDriver driver = getInstance();
			//driver.run();
		}
		catch(Exception e)
		{
			e.printStackTrace();
			log.error(e.getMessage(), e);
			System.exit(1);
		}
	}

	/**
	 * The server used to detect that individual connections are broken due to hardware failures.
	 * @return a {@link RecoveryServer} instance.
	 */
	public RecoveryServer getRecoveryServer()
	{
		return recoveryServer;
	}
}

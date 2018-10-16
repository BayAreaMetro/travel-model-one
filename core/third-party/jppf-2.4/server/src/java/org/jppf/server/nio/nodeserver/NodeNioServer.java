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

package org.jppf.server.nio.nodeserver;

import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

import org.jppf.comm.recovery.*;
import org.jppf.io.MultipleBuffersLocation;
import org.jppf.security.JPPFSecurityContext;
import org.jppf.server.JPPFDriver;
import org.jppf.server.job.JPPFJobManager;
import org.jppf.server.nio.*;
import org.jppf.server.protocol.*;
import org.jppf.server.queue.*;
import org.jppf.server.scheduler.bundle.Bundler;
import org.jppf.server.scheduler.bundle.spi.JPPFBundlerFactory;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * Instances of this class serve task execution requests to the JPPF nodes.
 * @author Laurent Cohen
 */
public class NodeNioServer extends NioServer<NodeState, NodeTransition> implements ReaperListener
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(NodeNioServer.class);
	/**
	 * Determines whether DEBUG logging level is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Determines whether TRACE logging level is enabled.
	 */
	private static boolean traceEnabled = log.isTraceEnabled();
	/**
	 * The algorithm that dynamically computes the task bundle size.
	 */
	private AtomicReference<Bundler> bundlerRef;
	/**
	 * The uuid for the task bundle sent to a newly connected node.
	 */
	static final String INITIAL_BUNDLE_UUID = JPPFDriver.getInstance().getUuid();
	/**
	 * The the task bundle sent to a newly connected node.
	 */
	private BundleWrapper initialBundle = null;
	/**
	 * Holds the currently idle channels.
	 */
	private List<ChannelWrapper<?>> idleChannels = new ArrayList<ChannelWrapper<?>>();
	/**
	 * A reference to the driver's tasks queue.
	 */
	private JPPFQueue queue = null;
	/**
	 * Used to create bundler instances.
	 */
	private JPPFBundlerFactory bundlerFactory = new JPPFBundlerFactory();
	/**
	 * Task that dispatches queued jobs to available nodes.
	 */
	private final TaskQueueChecker taskQueueChecker;
	/**
	 * Reference to the driver.
	 */
	private static JPPFDriver driver = JPPFDriver.getInstance();
	/**
	 * The thread polling the local channel.
	 */
	private ChannelSelectorThread selectorThread = null;
	/**
	 * The local channel, if any.
	 */
	private ChannelWrapper<?> localChannel = null;
	/**
	 * 
	 */
	private ExecutorService checkerExecutor = Executors.newSingleThreadExecutor(new JPPFThreadFactory("JobChecker"));
	/**
	 * Mapping of channels to their uuid.
	 */
	private Map<String, ChannelWrapper<?>> uuidMap = new HashMap<String, ChannelWrapper<?>>();

	/**
	 * Initialize this server with a specified port number.
	 * @param port the port this socket server is listening to.
	 * @throws Exception if the underlying server socket can't be opened.
	 */
	public NodeNioServer(int port) throws Exception
	{
		this(new int[] { port });
	}

	/**
	 * Initialize this server with the specified port numbers.
	 * @param ports the ports this socket server is listening to.
	 * @throws Exception if the underlying server socket can't be opened.
	 */
	public NodeNioServer(int[] ports) throws Exception
	{
		super(ports, "NodeServer", false);
		taskQueueChecker = new TaskQueueChecker(this);
		this.selectTimeout = 1L;
		Bundler bundler = bundlerFactory.createBundlerFromJPPFConfiguration();
		this.bundlerRef = new AtomicReference<Bundler>(bundler);
		((JPPFPriorityQueue) getQueue()).addQueueListener(new QueueListener()
		{
			public void newBundle(QueueEvent event)
			{
				selector.wakeup();
			}
		});
		RecoveryServer recoveryServer = JPPFDriver.getInstance().getRecoveryServer();
		if (recoveryServer != null) recoveryServer.getReaper().addReaperListener(this);
	}

	/**
	 * Initialize the local channel connection.
	 * @param localChannel the local channel to use.
	 */
	public void initLocalChannel(ChannelWrapper<?> localChannel)
	{
		if (JPPFConfiguration.getProperties().getBoolean("jppf.local.node.enabled", false))
		{
			this.localChannel = localChannel;
			ChannelSelector channelSelector = new LocalChannelSelector(localChannel, this);
			localChannel.setSelector(channelSelector);
			selectorThread = new ChannelSelectorThread(channelSelector, this);
			localChannel.setKeyOps(getInitialInterest());
			new Thread(selectorThread, "NodeChannelSelector").start();
			postAccept(localChannel);
		}
	}
	
	/**
	 * {@inheritDoc}
	 */
	protected NioServerFactory<NodeState, NodeTransition> createFactory()
	{
		return new NodeServerFactory(this);
	}

	/**
	 * {@inheritDoc}
	 */
	protected boolean externalStopCondition()
	{
		return driver.isShuttingDown();
	}

	/**
	 * {@inheritDoc}
	 */
	public void postAccept(ChannelWrapper channel)
	{
		driver.getStatsManager().newNodeConnection();
		AbstractNodeContext context = (AbstractNodeContext) channel.getContext();
		try
		{
			context.setBundle(getInitialBundle());
			transitionManager.transitionChannel(channel, NodeTransition.TO_SEND_INITIAL);
		}
		catch (Exception e)
		{
			log.error(e.getMessage(), e);
			closeNode(channel, context);
		}
	}

	/**
	 * {@inheritDoc}
	 */
	public void postSelect()
	{
		if (idleChannels.isEmpty() || getQueue().isEmpty()) return;
		if (!taskQueueChecker.isRunning())
		{
			taskQueueChecker.setRunning(true);
			checkerExecutor.submit(taskQueueChecker);
			//transitionManager.submit(taskQueueChecker);
		}
	}

	/**
	 * Add a channel to the list of idle channels.
	 * @param channel the channel to add to the list.
	 */
	public void addIdleChannel(ChannelWrapper<?> channel)
	{
		if (traceEnabled) log.trace("Adding idle channel " + channel);
		synchronized(idleChannels)
		{
			idleChannels.add(channel);
		}
	}

	/**
	 * Remove a channel from the list of idle channels.
	 * @param channel the channel to remove from the list.
	 * @return a reference to the removed channel.
	 */
	public ChannelWrapper<?> removeIdleChannel(ChannelWrapper<?> channel)
	{
		if (traceEnabled) log.trace("Removing idle channel " + channel);
		synchronized(idleChannels)
		{
			idleChannels.remove(channel);
		}
		return channel;
	}

	/**
	 * Remove the channel at the specified index from the list of idle channels.
	 * @param index the index of the channel to remove from the list.
	 * @return a reference to the removed channel.
	 */
	public ChannelWrapper<?>  removeIdleChannel(int index)
	{
		ChannelWrapper<?> channel = null;
		synchronized(idleChannels)
		{
			try
			{
				channel = idleChannels.remove(index);
				if (traceEnabled) log.trace("Removed idle chanel " + channel + " at index " + index);
			}
			catch(Exception e)
			{
				if (debugEnabled) log.debug("error removing channel at index " + index, e);
				else log.warn("error removing channel at index " + index + " : " + e.getMessage());
			}
		}
		return channel;
	}

	/**
	 * Define a context for a newly created channel.
	 * @return an <code>NioContext</code> instance.
	 * @see org.jppf.server.nio.NioServer#createNioContext()
	 */
	public NioContext createNioContext()
	{
		return new RemoteNodeContext();
	}

	/**
	 * Get the IO operations a connection is initially interested in.
	 * @return a bit-wise combination of the interests, taken from
	 * {@link java.nio.channels.SelectionKey SelectionKey} constants definitions.
	 * @see org.jppf.server.nio.NioServer#getInitialInterest()
	 */
	public int getInitialInterest()
	{
		return SelectionKey.OP_READ;
	}

	/**
	 * Get the task bundle sent to a newly connected node,
	 * so that it can check whether it is up to date, without having
	 * to wait for an actual request to be sent.
	 * @return a <code>BundleWrapper</code> instance, with no task in it.
	 */
	private BundleWrapper getInitialBundle()
	{
		if (initialBundle == null)
		{
			try
			{
				JPPFSecurityContext cred = driver.getCredentials();
				SerializationHelper helper = new SerializationHelperImpl();
				// serializing a null data provider.
				JPPFBuffer buf = helper.getSerializer().serialize(null);
				byte[] dataProviderBytes = new byte[4 + buf.getLength()];
				ByteBuffer bb = ByteBuffer.wrap(dataProviderBytes);
				bb.putInt(buf.getLength());
				bb.put(buf.getBuffer());
				JPPFTaskBundle bundle = new JPPFTaskBundle();
				bundle.setParameter(BundleParameter.JOB_ID, "server handshake");
				bundle.setBundleUuid(INITIAL_BUNDLE_UUID);
				bundle.setRequestUuid("0");
				bundle.getUuidPath().add(driver.getUuid());
				bundle.setTaskCount(0);
				bundle.setState(JPPFTaskBundle.State.INITIAL_BUNDLE);
				initialBundle = new BundleWrapper(bundle);
				initialBundle.setDataProvider(new MultipleBuffersLocation(new JPPFBuffer(dataProviderBytes, dataProviderBytes.length)));
			}
			catch(Exception e)
			{
				log.error(e.getMessage(), e);
			}
		}
		return initialBundle;
	}

	/**
	 * Close a connection to a node.
	 * @param channel a <code>SocketChannel</code> that encapsulates the connection.
	 * @param context the context data associated with the channel.
	 */
	public static void closeNode(ChannelWrapper<?> channel, AbstractNodeContext context)
	{
		// bug [993389 - Nodes are not removed from the console upon dying]
		try
		{
			channel.close();
		}
		catch (Exception e)
		{
			log.error(e.getMessage(), e);
		}
		try
		{
			driver.getStatsManager().nodeConnectionClosed();
			NodeNioServer server = driver.getNodeNioServer();
			driver.removeNodeInformation(channel);
			server.removeIdleChannel(channel);
			if (context != null)
			{
				String uuid = context.getNodeUuid();
				if (uuid != null)
				{
					server.removeUuid(uuid);
				}
			}
		}
		catch (Exception e)
		{
			log.error(e.getMessage(), e);
		}
	}

	/**
	 * Get the algorithm that dynamically computes the task bundle size.
	 * @return a <code>Bundler</code> instance.
	 */
	public Bundler getBundler()
	{
		return bundlerRef.get();
	}

	/**
	 * Set the algorithm that dynamically computes the task bundle size.
	 * @param bundler a <code>Bundler</code> instance.
	 */
	public void setBundler(Bundler bundler)
	{
		bundlerRef.set(bundler);
	}

	/**
	 * Get a reference to the driver's tasks queue.
	 * @return a <code>JPPFQueue</code> instance.
	 */
	protected JPPFQueue getQueue()
	{
		if (queue == null) queue = JPPFDriver.getQueue();
		return queue;
	}

	/**
	 * Get a reference to the driver's job manager.
	 * @return a <code>JPPFQueue</code> instance.
	 */
	protected JPPFJobManager getJobManager()
	{
		return driver.getJobManager();
	}

	/**
	 * Get the factory object used to create bundler instances.
	 * @return an instance of <code>JPPFBundlerFactory</code>.
	 */
	public JPPFBundlerFactory getBundlerFactory()
	{
		return bundlerFactory;
	}

	/**
	 * Get the list of currently idle channels.
	 * @return a list of <code>SelectableChannel</code> instances.
	 */
	public List<ChannelWrapper<?>> getIdleChannels()
	{
		return idleChannels;
	}

	/**
	 * {@inheritDoc}
	 */
	public void connectionFailed(ReaperEvent event)
	{
		ServerConnection c = event.getConnection();
		if (!c.isOk())
		{
			String uuid = c.getUuid();
			ChannelWrapper<?> channel = (uuid != null) ? removeUuid(uuid) : null;
			if (channel != null)
			{
				if (debugEnabled) log.debug("about to close channel = " + (channel.isOpen() ? channel : channel.getClass().getSimpleName()) + " with uuid = " + uuid);
				AbstractNodeContext context = (AbstractNodeContext) channel.getContext();
				if (context != null) context.handleException(channel);
				else
				{
					log.warn("found null context - a job may be stuck!");
					closeNode(channel, null);
				}
			}
		}
	}

	/**
	 * Get a channel from its uuid.
	 * @param uuid the uuid key to look up in the the map.
	 * @return channel the corresponding channel.
	 */
	ChannelWrapper<?> getChannelFromUuid(String uuid)
	{
		synchronized(uuidMap)
		{
			return uuidMap.get(uuid);
		}
	}

	/**
	 * Put the specified uuid / channel pair into the uuid map.
	 * @param uuid the uuid key to add to the map.
	 * @param channel the corresponding channel.
	 */
	void putUuid(String uuid, ChannelWrapper<?> channel)
	{
		synchronized(uuidMap)
		{
			uuidMap.put(uuid, channel);
		}
	}

	/**
	 * Remove the specified uuid entry from the uuid map.
	 * @param uuid the uuid key to remove from the map.
	 * @return channel the corresponding channel.
	 */
	ChannelWrapper<?> removeUuid(String uuid)
	{
		synchronized(uuidMap)
		{
			return uuidMap.remove(uuid);
		}
	}
}

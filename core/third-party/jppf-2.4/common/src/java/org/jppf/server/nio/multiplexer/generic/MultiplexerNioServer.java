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

package org.jppf.server.nio.multiplexer.generic;

import java.nio.channels.*;
import java.util.*;

import org.jppf.JPPFException;
import org.jppf.server.nio.*;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * Nio server managing connections to and from the multiplexer.
 * @author Laurent Cohen
 */
public class MultiplexerNioServer extends NioServer<MultiplexerState, MultiplexerTransition>
{
	/**
	 * Name given to this thread.
	 */
	private static final String THIS_NAME = "MultiplexerServer Thread";
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(MultiplexerNioServer.class);
	/**
	 * Determines whether the debug level is enabled in the log configuration, without the cost of a method call.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * The list of locally-bound multiplexer ports. 
	 */
	private Set<String> remoteMultiplexers = new HashSet<String>();
	/**
	 * Mapping of this multiplexer to remote ones.
	 * Each local multiplexer port is mapped to a <i>host:port</i> combination.
	 */
	private Map<String, HostPort> remoteMultiplexerMap = new HashMap<String, HostPort>();
	/**
	 * The list of application ports this multiplexer listens to. 
	 */
	private Set<Integer> boundPorts = new HashSet<Integer>();
	/**
	 * Mapping of local application ports to outbound multiplexer ports.
	 */
	private Map<Integer, String> boundToMultiplexerMap = new HashMap<Integer, String>();
	/**
	 * The list of multiplexer ports this multiplexer listens to. 
	 */
	private Set<Integer> multiplexerPorts = new HashSet<Integer>();

	/**
	 * Initialize this server.
	 * @throws JPPFException if the underlying server socket can't be opened.
	 */
	public MultiplexerNioServer() throws JPPFException
	{
		super(THIS_NAME);
		selectTimeout = 1L;
		configure();
	}

	/**
	 * Create the factory holding all the states and transition mappings.
	 * @return an <code>NioServerFactory</code> instance.
	 * @see org.jppf.server.nio.NioServer#createFactory()
	 */
	protected NioServerFactory<MultiplexerState, MultiplexerTransition> createFactory()
	{
		return new MultiplexerServerFactory(this);
	}

	/**
	 * Configure this server from the configuration file.
	 * @throws JPPFException if the configuration failed.
	 */
	private void configure() throws JPPFException
	{
		if (debugEnabled) log.debug("configuring the multiplexer");
		TypedProperties props = JPPFConfiguration.getProperties();
		String s = props.getString("multiplexer.ports");
		if (s != null)
		{
			int[] ports = StringUtils.parseIntValues(s);
			for (int port: ports) multiplexerPorts.add(port);
		}

		s = props.getString("remote.multiplexers");
		if (s != null)
		{
			String[] names = s.split("\\s");
			for (String name: names)
			{
				remoteMultiplexers.add(name);
				s = props.getString("remote.multiplexer." + name);
				if (s != null) remoteMultiplexerMap.put(name, StringUtils.parseHostPort(s));
			}
			s = props.getString("bound.ports");
			if (s == null) return;
			ports = StringUtils.parseIntValues(s);
			for (int port: ports)
			{
				boundPorts.add(port);
				String name = props.getString("mapping." + port, null);
				if (name != null) boundToMultiplexerMap.put(port, name);
			}
		}

		int n = multiplexerPorts.size() + boundPorts.size();
		ports = new int[n];
		int count = 0;
		for (Integer port: multiplexerPorts) ports[count++] = port;
		for (Integer port: boundPorts) ports[count++] = port;
		if (debugEnabled)
		{
			log.debug("multiplexerPorts: " + multiplexerPorts);
			log.debug("boundPorts: " + boundPorts);
			log.debug("remoteMultiplexers: " + remoteMultiplexers);
			log.debug("remoteMultiplexerMap: " + remoteMultiplexerMap);
			log.debug("boundToMultiplexerMap: " + boundToMultiplexerMap);
		}
		init(ports);
	}

	/**
	 * {@inheritDoc}
	 */
	public NioContext createNioContext()
	{
		return new MultiplexerContext();
	}

	/**
	 * {@inheritDoc}
	 */
	public int getInitialInterest()
	{
		return SelectionKey.OP_READ | SelectionKey.OP_WRITE;
	}

	/**
	 * {@inheritDoc}
	 */
	public void postAccept(ChannelWrapper key, ServerSocketChannel serverChannel)
	{
		int port = serverChannel.socket().getLocalPort();
		if (debugEnabled) log.debug("accepting on port " + port);
		MultiplexerContext context = (MultiplexerContext) key.getContext();
		if (multiplexerPorts.contains(port)) context.setMultiplexerPort(port);
		else if (boundPorts.contains(port)) context.setBoundPort(port);
		postAccept(key);
	}

	/**
	 * {@inheritDoc}
	 */
	public void postAccept(ChannelWrapper key)
	{
		MultiplexerContext context = (MultiplexerContext) key.getContext();
		if (context.isApplicationPort())
		{
			if (debugEnabled) log.debug("initializing outbound port " + context.getBoundPort());
			transitionManager.transitionChannel(key, MultiplexerTransition.TO_IDLE);
			HostPort mult = getHostPortForBoundPort(context.getBoundPort());
			MultiplexerChannelHandler handler = new MultiplexerChannelHandler(this, mult.host(), mult.port(), key);
			MultiplexerChannelInitializer init = new MultiplexerChannelInitializer(handler);
			new Thread(init).start();
		}
		else if (context.isMultiplexerPort())
		{
			if (debugEnabled) log.debug("initializing multiplexing port " + context.getMultiplexerPort());
			transitionManager.transitionChannel(key, MultiplexerTransition.TO_IDENTIFYING_INBOUND_CHANNEL);
		}
	}

	/**
	 * Get the outbound remote multiplexer associated with an inbound application port. 
	 * @param port the application port to lookup.
	 * @return a <code>HostPort</code> instannce, or null if no remote multiplexer could be found.
	 */
	public HostPort getHostPortForBoundPort(int port)
	{
		String name = boundToMultiplexerMap.get(port);
		if (name == null) return null;
		return remoteMultiplexerMap.get(name);
	}

	/**
	 * Entry point for the multiplexer application.
	 * @param args not used.
	 */
	public static void main(String...args)
	{
		try
		{
			MultiplexerNioServer svr = new MultiplexerNioServer();
			svr.start();
			svr.join();
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
			e.printStackTrace();
		}
	}
}

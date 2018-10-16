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
package org.jppf.ui.monitoring.data;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

import javax.swing.*;

import org.jppf.client.*;
import org.jppf.client.event.*;
import org.jppf.management.JMXDriverConnectionWrapper;
import org.jppf.server.JPPFStats;
import org.jppf.ui.monitoring.event.*;
import org.jppf.ui.options.*;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * This class provides a convenient access to the statistics obtained from the JPPF server.
 * @author Laurent Cohen
 */
public final class StatsHandler implements StatsConstants, ClientListener
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(StatsHandler.class);
	/**
	 * Determines whether debug log statements are enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Singleton instance of this class.
	 */
	//private static StatsHandler instance = null;
	private static AtomicReference<StatsHandler> instance = new AtomicReference<StatsHandler>();
	/**
	 * JPPF client used to submit execution requests.
	 */
	private JPPFClient jppfClient = null;
	/**
	 * The current client connection for which statistics and charts are displayed.
	 */
	private JPPFClientConnectionImpl currentConnection = null;
	/**
	 * The object holding the current statistics values.
	 */
	private JPPFStats stats = new JPPFStats();
	/**
	 * List of listeners registered with this stats formatter.
	 */
	private List<StatsHandlerListener> listeners = new ArrayList<StatsHandlerListener>();
	/**
	 * Timer used to query the stats from the server. 
	 */
	private java.util.Timer timer = null;
	/**
	 * Interval, in milliseconds, between refreshes from the server.
	 */
	private long refreshInterval = 2000L;
	/**
	 * Number of data snapshots kept in memory.
	 */
	private int rolloverPosition = 200;
	/**
	 * Contains all the data and its converted values received from the server.
	 */
	private Map<String, ConnectionDataHolder> dataHolderMap = new HashMap<String, ConnectionDataHolder>();
	/**
	 * Number of data updates so far.
	 */
	private int tickCount = 0;
	/**
	 * Option containing the combobox with the list of driver connections. 
	 */
	private OptionElement serverListOption = null;
	/**
	 * Thread pool used to process new conneciton events.
	 */
	private ExecutorService executor = Executors.newFixedThreadPool(1);

	/**
	 * Get the singleton instance of this class.
	 * @return a <code>StatsHandler</code> instance.
	 */
	public synchronized static StatsHandler getInstance()
	{
		if (instance.get() == null) instance.set(new StatsHandler());
		return instance.get();
	}

	/**
	 * Initialize this statistics handler.
	 */
	private StatsHandler()
	{
		if (debugEnabled) log.debug("initializing StatsHandler");
		refreshInterval = JPPFConfiguration.getProperties().getLong("default.refresh.interval", 1000L);
		if (refreshInterval > 0L) timer = new java.util.Timer("JPPF Driver Statistics Update Timer");
		getJppfClient(null);
		update(null, stats);
	}

	/**
	 * Stop the automatic refresh of the stats through a timer.
	 */
	public void stopRefreshTimer()
	{
		if (timer != null)
		{
			timer.cancel();
			timer = null;
		}
	}

	/**
	 * Get the interval between refreshes from the server.
	 * @return the interval in milliseconds.
	 */
	public long getRefreshInterval()
	{
		return refreshInterval;
	}

	/**
	 * Set the interval between refreshes from the server.
	 * @param refreshInterval the interval in milliseconds.
	 */
	public void setRefreshInterval(long refreshInterval)
	{
		this.refreshInterval = refreshInterval;
	}

	/**
	 * Request an update from the current server conenction.
	 */
	public void requestUpdate()
	{
		if (getCurrentConnection() == null) return;
		requestUpdate((JPPFClientConnectionImpl) getCurrentConnection());
	}

	/**
	 * Request an update from the server.
	 * @param c the client connection to request the data from.
	 */
	public void requestUpdate(JPPFClientConnectionImpl c)
	{
		try
		{
			if ((c != null) && JPPFClientConnectionStatus.ACTIVE.equals(c.getStatus()))
			{
				JPPFStats stats = c.getJmxConnection().statistics();
        if (stats != null) update(c, stats);
			}
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
		}
	}

	/**
	 * Request the server settings.
	 * @param algorithm - the name of the load-balancing algorithm to set on the server.
	 * @param params - the algorithm's parameters.
	 * @return the response message from the server.
	 */
	public String changeSettings(String algorithm, Map params)
	{
		if (getCurrentConnection() == null) return "No active server connection";
		String msg = null;
		try
		{
			if (debugEnabled) log.debug("command: CHANGE_SETTINGS, parameters: " + params);
			msg = (String) currentJmxConnection().changeLoadBalancerSettings(algorithm, params);
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
			msg = "An exception occurred:\n"+e.getMessage();
		}
		return msg;
	}

	/**
	 * Shutdown, and eventually restart, the server.
	 * @param shutdownDelay - the delay before shutting down.
	 * @param restartDelay - the delay, starting after shutdown, before restarting. If it is < 0, no restart occurs.
	 * @return the response message from the server.
	 */
	public String requestShutdownRestart(Number shutdownDelay, Number restartDelay)
	{
		if (getCurrentConnection() == null) return "No active server connection";
		String msg = null;
		try
		{
			return (String) currentJmxConnection().restartShutdown(shutdownDelay.longValue(), restartDelay.longValue());
		}
		catch(Exception e)
		{
			log.error(e.getMessage(), e);
			return "An exception occurred:\n"+e.getMessage();
		}
	}

	/**
	 * Update the current statistics with new values obtained from the server.
	 * @param connection - the client connection from which the data is obtained.
	 * @param stats - the object holding the new statistics values.
	 */
	public synchronized void update(JPPFClientConnection connection, JPPFStats stats)
	{
		if (stats == null) return;
		if (connection == null)
		{
			List<JPPFClientConnection> list = getJppfClient(null).getAllConnections();
			if ((list == null) || list.isEmpty()) return;
			else connection = getJppfClient(null).getAllConnections().get(0);
		}
		ConnectionDataHolder dataHolder = dataHolderMap.get(connection.getName());
		tickCount++;
		if (dataHolder == null) return;
		dataHolder.getDataList().add(stats);
		dataHolder.getStringValuesMaps().add(StatsFormatter.getStringValuesMap(stats));
		dataHolder.getDoubleValuesMaps().add(StatsFormatter.getDoubleValuesMap(stats));
		int diff = dataHolder.getDataList().size() - rolloverPosition;
		for (int i=0; i<diff; i++)
		{
			dataHolder.getDataList().remove(0);
			dataHolder.getStringValuesMaps().remove(0);
			dataHolder.getDoubleValuesMaps().remove(0);
		}
		if ((getCurrentConnection() != null) && connection.getName().equals(getCurrentConnection().getName()))
		{
			fireStatsHandlerEvent(StatsHandlerEvent.Type.UPDATE);
		}
	}

	/**
	 * Register a <code>StatsHandlerListener</code> with this stats formatter.
	 * @param listener - the listener to register.
	 */
	public void addStatsHandlerListener(StatsHandlerListener listener)
	{
		if (listener != null) listeners.add(listener);
	}

	/**
	 * Unregister a <code>StatsHandlerListener</code> from this stats formatter.
	 * @param listener - the listener to unregister.
	 */
	public void removeStatsHandlerListener(StatsHandlerListener listener)
	{
		if (listener != null) listeners.remove(listener);
	}

	/**
	 * Notify all listeners of a change in this stats formatter.
	 * @param type - the type of event to fire.
	 */
	public void fireStatsHandlerEvent(StatsHandlerEvent.Type type)
	{
		StatsHandlerEvent event = new StatsHandlerEvent(this, type);
		for (StatsHandlerListener listener: listeners) listener.dataUpdated(event);
	}

	/**
	 * Get the number of data snapshots kept in memory.
	 * @return the rollover position as an int value.
	 */
	public synchronized int getRolloverPosition()
	{
		return rolloverPosition;
	}

	/**
	 * Set the number of data snapshots kept in memory. If the value if less than the former values, the corresponding,
	 * older, data snapshots will be deleted. 
	 * @param rolloverPosition - the rollover position as an int value.
	 */
	public synchronized void setRolloverPosition(int rolloverPosition)
	{
		if (rolloverPosition <= 0) throw new IllegalArgumentException("zero or less not accepted: "+rolloverPosition);
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		int diff = dataHolder.getDataList().size() - rolloverPosition;
		for (int i=0; i<diff; i++)
		{
			dataHolder.getDataList().remove(0);
			dataHolder.getStringValuesMaps().remove(0);
			dataHolder.getDoubleValuesMaps().remove(0);
		}
		this.rolloverPosition = rolloverPosition;
	}

	/**
	 * Get the current number of data snapshots.
	 * @return the number of snapshots as an int.
	 */
	public int getStatsCount()
	{
		if (getCurrentConnection() == null) return 0;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		return dataHolder.getDataList().size();
	}

	/**
	 * Get the data snapshot at a specified position.
	 * @param position - the position to get the data at.
	 * @return a <code>JPPFStats</code> instance.
	 */
	public synchronized JPPFStats getStats(int position)
	{
		if (getCurrentConnection() == null) return stats;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		return dataHolder.getDataList().get(position);
	}

	/**
	 * Get the latest data snapshot.
	 * @return a <code>JPPFStats</code> instance.
	 */
	public JPPFStats getLatestStats()
	{
		return getStats(getStatsCount() - 1);
	}

	/**
	 * Get the mapping of a data snapshot's fields, at a specified position, to their corresponding string values.
	 * @param position - the position to get the data at.
	 * @return a map of field names to their values represented as strings.
	 */
	public synchronized Map<Fields, String> getStringValues(int position)
	{
		if (getCurrentConnection() == null) return null;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		return dataHolder.getStringValuesMaps().get(position);
	}

	/**
	 * Get the mapping of the most recent data snapshot's fields to their corresponding string values.
	 * @return a map of field names to their values represented as strings.
	 */
	public Map<Fields, String> getLatestStringValues()
	{
		if (getCurrentConnection() == null) return null;
		int n = getStatsCount() - 1;
		if (n < 0) return null;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		List<Map<Fields, String>> list = dataHolder.getStringValuesMaps();
		if (n < list.size()) return list.get(n);
		return list.get(list.size()-1);
	}

	/**
	 * Get the mapping of a data snapshot's fields, at a specified position, to their corresponding double values.
	 * @param position - the position to get the data at.
	 * @return a map of field names to their values represented as double values.
	 */
	public synchronized Map<Fields, Double> getDoubleValues(int position)
	{
		if (getCurrentConnection() == null) return null;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		return dataHolder.getDoubleValuesMaps().get(position);
	}

	/**
	 * Get the mapping of the most recent data snapshot's fields to their corresponding double values.
	 * @return a map of field names to their values represented as double values.
	 */
	public Map<Fields, Double> getLatestDoubleValues()
	{
		if (getCurrentConnection() == null) return null;
		int n = getStatsCount() - 1;
		if (n < 0) return null;
		ConnectionDataHolder dataHolder = dataHolderMap.get(getCurrentConnection().getName());
		List<Map<Fields, Double>> list = dataHolder.getDoubleValuesMaps();
		if (n < list.size()) return list.get(n);
		return list.get(list.size()-1);
	}

	/**
	 * Get the number of data updates so far.
	 * @return the nuber of updates as an int.
	 */
	public int getTickCount()
	{
		return tickCount;
	}

	/**
	 * Get the current client connection for which statistics and charts are displayed.
	 * @return a <code>JPPFClientConnection</code> instance.
	 */
	public synchronized JPPFClientConnection getCurrentConnection()
	{
		return currentConnection;
	}

	/**
	 * Set the current client connection for which statistics and charts are displayed.
	 * @param connection a <code>JPPFClientConnection</code> instance.
	 */
	public synchronized void setCurrentConnection(final JPPFClientConnectionImpl connection)
	{
		if ((currentConnection == null) || ((connection != null) && !connection.getName().equals(currentConnection.getName())))
		{
			SwingUtilities.invokeLater(new Runnable()
			{
				public void run()
				{
					currentConnection = connection;
					if (JPPFClientConnectionStatus.ACTIVE.equals(connection.getStatus()))
					{
						fireStatsHandlerEvent(StatsHandlerEvent.Type.RESET);
					}
				}
			});
		}
	}

	/**
	 * JPPF client used to submit data udpate and administration requests.
	 * @param clientListener a listener to register with the JPPF client.
	 * @return a <code>JPPFClient</code> instance.
	 */
	public synchronized JPPFClient getJppfClient(ClientListener clientListener)
	{
		if (jppfClient == null)
		{
			jppfClient = (clientListener == null) ? new JPPFClient(this) : new JPPFClient(this, clientListener);
		}
		return jppfClient;
	}

	/**
	 * Notifiy this listener that a new driver connection was created.
	 * @param event the event to notify this listener of.
	 * @see org.jppf.client.event.ClientListener#newConnection(org.jppf.client.event.ClientEvent)
	 */
	public synchronized void newConnection(ClientEvent event)
	{
		executor.submit(new NewConnectionTask(event.getConnection()));
	}

	/**
	 * Get the option containing the combobox with the list of driver connections. 
	 * @return an <code>OptionElement</code> instance.
	 */
	public synchronized OptionElement getServerListOption()
	{
		return serverListOption;
	}

	/**
	 * Set the option containing the combobox with the list of driver connections. 
	 * @param serverListOption an <code>OptionElement</code> instance.
	 */
	public synchronized void setServerListOption(OptionElement serverListOption)
	{
		this.serverListOption = serverListOption;
		if (debugEnabled) log.debug("setting serverList option=" + serverListOption);
		List<JPPFClientConnection> list = getJppfClient(null).getAllConnections();
		for (JPPFClientConnection c: list)executor.submit(new NewConnectionTask(c));
		notifyAll();
	}

	/**
	 * Get the JMX connection for the current driver connection.
	 * @return a <code>JMXDriverConnectionWrapper</code> instance.
	 */
	public JMXDriverConnectionWrapper currentJmxConnection()
	{
		JPPFClientConnectionImpl c = (JPPFClientConnectionImpl) getCurrentConnection();
		if (c == null) return null;
		return c.getJmxConnection();
	}

	/**
	 * Task executed when a new driver connection is created.
	 */
	private class NewConnectionTask extends ThreadSynchronization implements Runnable
	{
		/**
		 * The new connection that was created.
		 */
		private JPPFClientConnection c = null;

		/**
		 * Initialized this task with the specified client connection.
		 * @param c the new connection that was created.
		 */
		public NewConnectionTask(JPPFClientConnection c)
		{
			this.c = c;
		}

		/**
		 * Perform the task.
		 * @see java.lang.Runnable#run()
		 */
		public void run()
		{
			if (dataHolderMap.get(c.getName()) == null)
			{
				dataHolderMap.put(c.getName(), new ConnectionDataHolder());
			}
			if (timer != null)
			{
				TimerTask task = new StatsRefreshTask((JPPFClientConnectionImpl) c);
				timer.schedule(task, 1000L, refreshInterval);
			}
			JComboBox box = null;
			while (getServerListOption() == null) goToSleep(50L);
			synchronized(StatsHandler.this)
			{
				if (debugEnabled) log.debug("adding client connection " + c.getName());
				box = ((ComboBoxOption) getServerListOption()).getComboBox();
				int count = box.getItemCount();
				boolean found = false;
				for (int i=0; i<count; i++)
				{
					Object o = box.getItemAt(i);
					if (c.equals(o))
					{
						found = true;
						break;
					}
				}
				if (!found)
				{
					box.addItem(c);
					int maxLen = 0;
					Object proto = null;
					for (int i=0; i<box.getItemCount(); i++)
					{
						Object o = box.getItemAt(i);
						int n = o.toString().length();
						if (n > maxLen)
						{
							maxLen = n;
							proto = o;
						}
					}
					if (proto != null) box.setPrototypeDisplayValue(proto);
				}
				if (currentConnection == null)
				{
					currentConnection = (JPPFClientConnectionImpl) c;
					box.setSelectedItem(c);
				}
			}
		}
	}
}

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
package org.jppf.server.protocol;

import java.io.Serializable;
import java.text.*;
import java.util.*;

import org.jppf.scheduling.JPPFSchedule;
import org.jppf.task.storage.DataProvider;

/**
 * Abstract superclass for all tasks submitted to the execution server.
 * This class provides the basic facilities to handle data shared among tasks, handling of task execution exception,
 * and handling of the execution results.<p>
 * JPPF clients have to extend this class and must implement the <code>run</code> method. In the
 * <code>run</code> method the task calculations are performed, and the result of the calculations
 * is set with the {@link #setResult(Object)} method:
 * <pre>
 * class MyTask extends JPPFTask {
 *   public void run() {
 *     // do the calculation ...
 *     setResult(myResult);
 *   }
 * }
 * </pre>
 * @author Laurent Cohen
 */
public abstract class JPPFTask implements Runnable, Serializable
{
	/**
	 * Explicit serialVersionUID.
	 */
	private static final long serialVersionUID = 1L;
	/**
	 * The position of this task at the submission time.
	 */
	private int position;
	/**
	 * The result of the task execution.
	 */
	private Object result = null;
	/**
	 * The exception that was raised by this task's execution.
	 */
	private Exception exception = null;
	/**
	 * The provider of shared data for this task.
	 */
	private transient DataProvider dataProvider = null;
	/**
	 * List of listeners for this task.
	 */
	protected transient List<JPPFTaskListener> listeners = null;
	/**
	 * The task timeout schedule configuration.
	 */
	private JPPFSchedule timeoutSchedule = null;

	/**
	 * Default constructor.
	 */
	public JPPFTask()
	{
	}

	/**
	 * A user-assigned id for this task.<br>
	 * This id is used as a task identifier when cancelling or restarting a task
	 * using the remote management functionalities.
	 */
	private String id = null;

	/**
	 * Get the result of the task execution.
	 * @return the result as an array of bytes.
	 */
	public Object getResult()
	{
		return result;
	}

	/**
	 * Set the result of the task execution.
	 * @param  result the result of this task's execution.
	 */
	public void setResult(Object  result)
	{
		this.result = result;
	}

	/**
	 * Get the exception that was raised by this task's execution. If the task raised a
	 * {@link Throwable}, the exception is embedded into a {@link org.jppf.JPPFException}.
	 * @return a <code>Exception</code> instance, or null if no exception was raised.
	 */
	public Exception getException()
	{
		return exception;
	}

	/**
	 * Sets the exception that was raised by this task's execution in the <code>run</code> method.
	 * The exception is set by the JPPF framework.
	 * @param exception a <code>ClientApplicationException</code> instance.
	 */
	public void setException(Exception exception)
	{
		this.exception = exception;
	}

	/**
	 * Get the provider of shared data for this task.
	 * @return a <code>DataProvider</code> instance. 
	 */
	public DataProvider getDataProvider()
	{
		return dataProvider;
	}

	/**
	 * Set the provider of shared data for this task.
	 * @param dataProvider a <code>DataProvider</code> instance.
	 */
	public void setDataProvider(DataProvider dataProvider)
	{
		this.dataProvider = dataProvider;
	}

	/**
	 * Returns the position of this task at the submission.
	 * @return Returns the position of this task at the submission.
	 */
	public final int getPosition() {
		return position;
	}

	/**
	 * Sets the position of this task into the submission.
	 * @param position The position of this task into the submission.
	 */
	public final void setPosition(int position) {
		this.position = position;
	}

	/**
	 * Add a connection status listener to this connection's list of listeners.
	 * @param listener the listener to add to the list.
	 */
	public synchronized void addJPPFTaskListener(JPPFTaskListener listener)
	{
		getListeners().add(listener);
	}

	/**
	 * Remove a connection status listener from this connection's list of listeners.
	 * @param listener the listener to remove from the list.
	 */
	public synchronized void removeJPPFTaskListener(JPPFTaskListener listener)
	{
		getListeners().remove(listener);
	}

	/**
	 * Notify all listeners that an event has occurred within this task.
	 * @param source an object describing the event, must be serializable.
	 */
	public synchronized void fireNotification(Serializable source)
	{
		JPPFTaskEvent event = new JPPFTaskEvent(source);
		// to avoid ConcurrentModificationException
		JPPFTaskListener[] array = getListeners().toArray(new JPPFTaskListener[0]);
		for (JPPFTaskListener listener: array) listener.eventOccurred(event);
	}

	/**
	 * Get the list of listeners for this task.
	 * @return a list of <code>JPPFTaskListener</code> instances.
	 */
	protected synchronized List<JPPFTaskListener> getListeners()
	{
		if (listeners == null) listeners = new ArrayList<JPPFTaskListener>();
		return listeners;
	}

	/**
	 * Get the timeout for this task.
	 * @return the timeout in milliseconds.
	 */
	public long getTimeout()
	{
		if (timeoutSchedule == null) return 0L;
		return timeoutSchedule.getDuration();
	}

	/**
	 * Set the timeout for this task.
	 * @param timeout the timeout in milliseconds.
	 */
	public void setTimeout(long timeout)
	{
		timeoutSchedule = new JPPFSchedule(timeout);
	}

	/**
	 * Get the timeout date for this task.
	 * @return the date in string format.
	 */
	public String getTimeoutDate()
	{
		if (timeoutSchedule == null) return null;
		return timeoutSchedule.getDate();
	}

	/**
	 * Get the format of timeout date for this task.
	 * @return a <code>SimpleDateFormat</code> instance.
	 * @deprecated use {@link #getTimeoutFormat() getTimeoutFormat()} instead.
	 */
	public SimpleDateFormat getTimeoutDateFormat()
	{
		if (timeoutSchedule == null) return null;
		return new SimpleDateFormat(timeoutSchedule.getFormat());
	}

	/**
	 * Get the format of timeout date for this task.
	 * @return the timeout date format as a string pattern, as decribed in the specification for {@link SimpleDateFormat}.
	 */
	public String getTimeoutFormat()
	{
		if (timeoutSchedule == null) return null;
		return timeoutSchedule.getFormat();
	}

	/**
	 * Set the timeout date for this task.<br>
	 * Calling this method will reset the timeout value, as both timeout duration and timeout date
	 * are mutually exclusive.
	 * @param timeoutDate the date to set in string representation.
	 * @param timeoutDateFormat the format of of the date to set.
	 * @deprecated use {@link #setTimeoutDate(java.lang.String, java.lang.String) getTimeoutFormat(String, String)} instead.
	 */
	public void setTimeoutDate(String timeoutDate, SimpleDateFormat timeoutDateFormat)
	{
		timeoutSchedule = new JPPFSchedule(timeoutDate, timeoutDateFormat.toPattern());
	}

	/**
	 * Set the timeout date for this task.<br>
	 * Calling this method will reset the timeout value, as both timeout duration and timeout date are mutually exclusive.
	 * @param timeoutDate the date to set in string representation.
	 * @param format the format of of the date to set, as described in the specfication for {@link SimpleDateFormat}.
	 * @see java.text.SimpleDateFormat
	 */
	public void setTimeoutDate(String timeoutDate, String format)
	{
		timeoutSchedule = new JPPFSchedule(timeoutDate, format);
	}

	/**
	 * Get the user-assigned id for this task.
	 * @return the id as a string.
	 */
	public String getId()
	{
		return id;
	}

	/**
	 * Set the user-assigned id for this task.
	 * @param id the id as a string.
	 */
	public void setId(String id)
	{
		this.id = id;
	}

	/**
	 * Callback invoked when this task is cancelled.
	 * The default implementation does nothing and should be overriden by
	 * subclasses that desire to implement a specific behaviour on cancellation.
	 */
	public void onCancel()
	{
	}

	/**
	 * Callback invoked when this task is restarted.
	 * The default implementation does nothing and should be overriden by
	 * subclasses that desire to implement a specific behaviour on restart.
	 */
	public void onRestart()
	{
	}

	/**
	 * Callback invoked when this task times out.
	 * The default implementation does nothing and should be overriden by
	 * subclasses that desire to implement a specific behaviour on timeout.
	 */
	public void onTimeout()
	{
	}


	/**
	 * Get the <code>JPPFRunnable</code>-annotated object or POJO wrapped by this task.
	 * @return an objet or class that is JPPF-annotated.
	 */
	public Object getTaskObject()
	{
		return null;
	}

	/**
	 * Get the task timeout schedule configuration.
	 * @return a <code>JPPFScheduleConfiguration</code> instance.
	 */
	public JPPFSchedule getTimeoutSchedule()
	{
		return timeoutSchedule;
	}

	/**
	 * Get the task timeout schedule configuration.
	 * @param timeoutSchedule a <code>JPPFScheduleConfiguration</code> instance. 
	 */
	public void setTimeoutSchedule(JPPFSchedule timeoutSchedule)
	{
		this.timeoutSchedule = timeoutSchedule;
	}
}

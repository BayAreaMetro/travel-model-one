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
package org.jppf.server.job;

import java.util.List;

import org.jppf.job.*;
import org.jppf.management.JPPFManagementInfo;
import org.jppf.server.JPPFDriver;
import org.jppf.server.nio.ChannelWrapper;
import org.jppf.server.protocol.*;

/**
 * Instances of this class are submitted into an event queue and generate actual
 * job manager events that are then dispatched to registered listeners.
 */
public class JobEventTask implements Runnable
{
	/**
	 * The job manager that submits the events.
	 */
	private JPPFJobManager jobManager = null;
	/**
	 * The type of event to generate.
	 */
	private JobEventType eventType = null;
	/**
	 * The node, if any, for which the event happened.
	 */
	private ChannelWrapper channel = null;
	/**
	 * The job data.
	 */
	private JPPFTaskBundle bundle = null;
	/**
	 * Creation timestamp for this task.
	 */
	private final long timestamp = System.currentTimeMillis();

	/**
	 * Initialize this job manager event task with the specified parameters.
	 * @param jobManager - the job manager that submits the events.
	 * @param eventType - the type of event to generate.
	 * @param bundle - the job data.
	 * @param channel - the id of the job source of the event.
	 */
	public JobEventTask(JPPFJobManager jobManager, JobEventType eventType, JPPFTaskBundle bundle, ChannelWrapper channel)
	{
		this.jobManager = jobManager;
		this.eventType = eventType;
		this.channel = channel;
		this.bundle = bundle;
	}

	/**
	 * Execute this task.
	 * @see java.lang.Runnable#run()
	 */
	public void run()
	{
		JPPFJobSLA sla = bundle.getJobSLA();
		Boolean pending = (Boolean) bundle.getParameter(BundleParameter.JOB_PENDING);
		JobInformation jobInfo = new JobInformation(bundle.getJobUuid(), bundle.getId(), bundle.getTaskCount(),
			bundle.getInitialTaskCount(), sla.getPriority(), sla.isSuspended(), (pending != null) && pending);
		jobInfo.setMaxNodes(sla.getMaxNodes());
		JPPFManagementInfo nodeInfo = (channel == null) ? null : JPPFDriver.getInstance().getNodeInformation(channel);
		JobNotification event = new JobNotification(eventType, jobInfo, nodeInfo, timestamp);
		List<JobListener> listeners = jobManager.getJobListeners();
		synchronized(listeners)
		{
			switch (eventType)
			{
				case JOB_QUEUED:
					for (JobListener listener: listeners) listener.jobQueued(event);
					break;

				case JOB_ENDED:
					for (JobListener listener: listeners) listener.jobEnded(event);
					break;

				case JOB_UPDATED:
					Integer n = (Integer) bundle.getParameter("real.task.count");
					if (n != null) jobInfo.setTaskCount(n);
					for (JobListener listener: listeners) listener.jobUpdated(event);
					break;

				case JOB_DISPATCHED:
					for (JobListener listener: listeners) listener.jobDispatched(event);
					break;

				case JOB_RETURNED:
					for (JobListener listener: listeners) listener.jobReturned(event);
					break;
			}
		}
	}
}

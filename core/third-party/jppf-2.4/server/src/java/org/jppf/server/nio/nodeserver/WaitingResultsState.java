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

import static org.jppf.server.nio.nodeserver.NodeTransition.*;

import org.jppf.management.JPPFSystemInformation;
import org.jppf.server.nio.ChannelWrapper;
import org.jppf.server.protocol.*;
import org.jppf.server.scheduler.bundle.*;
import org.slf4j.*;

/**
 * This class performs performs the work of reading a task bundle execution response from a node. 
 * @author Laurent Cohen
 */
class WaitingResultsState extends NodeServerState
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(WaitingResultsState.class);
	/**
	 * Determines whether DEBUG logging level is enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();

	/**
	 * Initialize this state.
	 * @param server the server that handles this state.
	 */
	public WaitingResultsState(NodeNioServer server)
	{
		super(server);
	}

	/**
	 * Execute the action associated with this channel state.
	 * @param wrapper the selection key corresponding to the channel and selector for this state.
	 * @return a state transition as an <code>NioTransition</code> instance.
	 * @throws Exception if an error occurs while transitioning to another state.
	 * @see org.jppf.server.nio.NioState#performTransition(java.nio.channels.SelectionKey)
	 */
	public NodeTransition performTransition(ChannelWrapper<?> wrapper) throws Exception
	{
		AbstractNodeContext context = (AbstractNodeContext) wrapper.getContext();
		if (context.getNodeMessage() == null) context.setNodeMessage(context.newMessage(), wrapper);
		if (context.readMessage(wrapper))
		{
			BundleWrapper bundleWrapper = context.getBundle();
			JPPFTaskBundle bundle = bundleWrapper.getBundle();
			BundleWrapper newBundleWrapper = context.deserializeBundle();
			JPPFTaskBundle newBundle = newBundleWrapper.getBundle();
			if (debugEnabled) log.debug("read bundle" + newBundle + " from node " + wrapper + " done");
			// if an exception prevented the node from executing the tasks
			if (newBundle.getParameter(BundleParameter.NODE_EXCEPTION_PARAM) != null)
			{
				if (debugEnabled)
				{
					Throwable t = (Throwable) newBundle.getParameter(BundleParameter.NODE_EXCEPTION_PARAM);
					log.debug("node " + wrapper + " returned exception parameter in the header for job '" + newBundle.getId() + "' : " + t);
				}
				newBundleWrapper.setTasks(bundleWrapper.getTasks());
				newBundle.setTaskCount(bundle.getTaskCount());
			}
			else
			{
				//long elapsed = System.currentTimeMillis() - bundle.getExecutionStartTime();
				long elapsed = (System.nanoTime() - bundle.getExecutionStartTime())/1000000;
				statsManager.taskExecuted(newBundle.getTaskCount(), elapsed, newBundle.getNodeExecutionTime(), context.getNodeMessage().getLength());
				context.getBundler().feedback(newBundle.getTaskCount(), elapsed);
			}
			boolean requeue = (Boolean) newBundle.getParameter(BundleParameter.JOB_REQUEUE, false);
			jobManager.jobReturned(bundleWrapper, wrapper);
			if (requeue)
			{
				bundle.setParameter(BundleParameter.JOB_REQUEUE, true);
				bundle.getJobSLA().setSuspended(true);
				context.setBundle(null);
				context.resubmitBundle(bundleWrapper);
			}
			else
			{
				if (!context.isJobCanceled())
				{
					// notify the client thread about the end of a bundle
					TaskCompletionListener listener = bundle.getCompletionListener();
					if (listener != null) listener.taskCompleted(newBundleWrapper);
				}
				else context.setJobCanceled(false);
			}
			Bundler bundler = context.getBundler();
			JPPFSystemInformation systemInfo = (JPPFSystemInformation) bundle.getParameter(BundleParameter.NODE_SYSTEM_INFO_PARAM);
			if ((systemInfo != null) && (bundler instanceof NodeAwareness)) ((NodeAwareness) bundler).setNodeConfiguration(systemInfo);
			// there is nothing left to do, so this instance will wait for a task bundle
			// make sure the context is reset so as not to resubmit the last bundle executed by the node.
			context.setNodeMessage(null, wrapper);
			context.setBundle(null);
			server.addIdleChannel(wrapper);
			return TO_IDLE;
		}
		return TO_WAITING;
	}
}

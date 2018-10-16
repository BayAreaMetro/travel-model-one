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
package org.jppf.ui.monitoring.node.actions;

import java.awt.event.*;
import java.util.List;

import javax.swing.*;

import org.jppf.management.JMXNodeConnectionWrapper;
import org.jppf.ui.monitoring.node.TopologyData;
import org.jppf.ui.options.*;
import org.jppf.ui.options.factory.OptionsHandler;
import org.jppf.ui.utils.GuiUtils;
import org.slf4j.*;

/**
 * This action displays an input panel for the user to type a new
 * thread pool size for a node, and updates the node with it.
 */
public class NodeThreadsAction extends AbstractTopologyAction
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(NodeThreadsAction.class);
	/**
	 * Determines whether debug log statements are enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Determines whether the "OK" button was pressed.
	 */
	private boolean isOk = false;
	/**
	 * Panel containing the dialog for entering the number of threads and their priority.
	 */
	private OptionElement panel = null;
	/**
	 * Number of threads.
	 */
	private int nbThreads = 1;
	/**
	 * Threads priority.
	 */
	private int priority = Thread.NORM_PRIORITY;

	/**
	 * Initialize this action.
	 */
	public NodeThreadsAction()
	{
		setupIcon("/org/jppf/ui/resources/threads.gif");
		setupNameAndTooltip("update.threads");
	}

	/**
	 * Update this action's enabled state based on a list of selected elements.
	 * @param selectedElements - a list of objects.
	 * @see org.jppf.ui.actions.AbstractUpdatableAction#updateState(java.util.List)
	 */
	public void updateState(List<Object> selectedElements)
	{
		super.updateState(selectedElements);
		setEnabled(nodeDataArray.length > 0);
	}

	/**
	 * Perform the action.
	 * @param event not used.
	 * @see java.awt.event.ActionListener#actionPerformed(java.awt.event.ActionEvent)
	 */
	public void actionPerformed(ActionEvent event)
	{
		AbstractButton btn = (AbstractButton) event.getSource();
		if (btn.isShowing()) location = btn.getLocationOnScreen();
		if (selectedElements.isEmpty()) return;
		try
		{
			panel = OptionsHandler.loadPageFromXml("org/jppf/ui/options/xml/NodeThreadPoolPanel.xml");
			if (nodeDataArray.length == 1)
			{
				nbThreads = nodeDataArray[0].getNodeState().getThreadPoolSize();
				priority = nodeDataArray[0].getNodeState().getThreadPriority();
			}
			((AbstractOption) panel.findFirstWithName("nbThreads")).setValue(nbThreads);
			((AbstractOption) panel.findFirstWithName("threadPriority")).setValue(priority);

			JButton okBtn = (JButton) panel.findFirstWithName("/nodeThreadsOK").getUIComponent();
			JButton cancelBtn = (JButton) panel.findFirstWithName("/nodeThreadsCancel").getUIComponent();
			final JFrame frame = new JFrame("Enter the number of threads and their priority");
			frame.setIconImage(GuiUtils.loadIcon("/org/jppf/ui/resources/threads.gif").getImage());
			okBtn.addActionListener(new ActionListener()
			{
				public void actionPerformed(ActionEvent event)
				{
					frame.setVisible(false);
					frame.dispose();
					doOK();
				}
			});
			cancelBtn.addActionListener(new ActionListener()
			{
				public void actionPerformed(ActionEvent event)
				{
					frame.setVisible(false);
					frame.dispose();
				}
			});
			frame.getContentPane().add(panel.getUIComponent());
			frame.pack();
			frame.setLocationRelativeTo(null);
			frame.setLocation(location);
			frame.setVisible(true);
		}
		catch(Exception e)
		{
			if (debugEnabled) log.debug(e.getMessage(), e);
		}
	}

	/**
	 * Perform the action.
	 */
	private void doOK()
	{
		AbstractOption nbThreadsOption = (AbstractOption) panel.findFirstWithName("nbThreads");
		AbstractOption priorityOption = (AbstractOption) panel.findFirstWithName("threadPriority");
		nbThreads = (Integer) nbThreadsOption.getValue();
		priority = (Integer) priorityOption.getValue();
		Runnable r = new Runnable()
		{
			public void run()
			{
				for (TopologyData data: nodeDataArray)
				{
					try
					{
						JMXNodeConnectionWrapper jmx = (JMXNodeConnectionWrapper) data.getJmxWrapper();
						jmx.updateThreadPoolSize(nbThreads);
						jmx.updateThreadsPriority(priority);
					}
					catch(Exception e)
					{
						log.error(e.getMessage(), e);
					}
				}
			}
		};
		new Thread(r).start();
	}
}

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

package org.jppf.ui.monitoring.job;

import org.jppf.ui.actions.JTreeTableActionHandler;
import org.jppf.ui.treetable.JTreeTable;

/**
 * Action handler for the JOb Data Panel.
 * @author Laurent Cohen
 */
public class JobDataPanelActionManager extends JTreeTableActionHandler
{
	/**
	 * Initialize this action manager with the specified JTreeTable component.
	 * @param treeTable - the JTreeTable whose actions are managed.
	 */
	public JobDataPanelActionManager(JTreeTable treeTable)
	{
		super(treeTable);
	}
}

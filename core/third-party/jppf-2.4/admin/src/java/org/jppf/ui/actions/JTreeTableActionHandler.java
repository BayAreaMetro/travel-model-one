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

package org.jppf.ui.actions;

import javax.swing.event.*;
import javax.swing.tree.*;

import org.jppf.ui.treetable.JTreeTable;

/**
 * Abstract implementation of the <code>ActionManager</code> interface for <code>JTreeTable</code> components.
 * @author Laurent Cohen
 */
public class JTreeTableActionHandler extends AbstractActionHandler
{
	/**
	 * The JTreeTable whose actions are managed.
	 */
	protected JTreeTable treeTable = null;

	/**
	 * Initialize this action manager with the specified JTreeTable component.
	 * @param treeTable - the JTreeTable whose actions are managed.
	 */
	public JTreeTableActionHandler(JTreeTable treeTable)
	{
		this.treeTable = treeTable;
		treeTable.getSelectionModel().addListSelectionListener(new ListSelectionListener()
		{
			public void valueChanged(ListSelectionEvent e)
			{
				synchronized(JTreeTableActionHandler.this)
				{
					computeSelectedElements();
					updateActions();
				}
			}
		});
	}

	/**
	 * Compute the list of elements selected in the component.
	 */
	protected synchronized void computeSelectedElements()
	{
		selectedElements.clear();
		int[] rows = treeTable.getSelectedRows();
		if ((rows == null) || (rows.length <= 0)) return;
		for (int n: rows)
		{
			TreePath path = treeTable.getTree().getPathForRow(n);
			if (path == null) continue;
			DefaultMutableTreeNode node = (DefaultMutableTreeNode) path.getLastPathComponent();
			selectedElements.add(node.getUserObject());
		}
	}
}

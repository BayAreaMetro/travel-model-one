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

package org.jppf.test.setup;

/**
 * Used to launch a single node.
 * @author Laurent Cohen
 */
public class NodeProcessLauncher extends GenericProcessLauncher
{
	/**
	 * Initialize the node launcher with the specified node id.
	 * @param n the id of the node, used to determine which cnfiguration files to use.
	 */
	public NodeProcessLauncher(int n)
	{
		super();
		setMainClass("org.jppf.node.NodeRunner");
		//addArgument("noLauncher");
		setJppfConfig("node" + n + ".properties");
		setLog4j("log4j-node" + n + ".properties");
		addClasspathElement("test/classes/config");
	}
}

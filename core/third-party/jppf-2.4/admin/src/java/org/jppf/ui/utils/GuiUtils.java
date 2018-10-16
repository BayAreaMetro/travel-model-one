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
package org.jppf.ui.utils;

import java.awt.*;
import java.net.URL;
import java.util.*;
import java.util.regex.*;

import javax.swing.*;

/**
 * Collection of GUI utility methods.
 * @author Laurent Cohen
 */
public final class GuiUtils
{
	/**
	 * A mapping of icons to their path, to use as an icon cache.
	 */
	private static Map<String, ImageIcon> iconMap = new Hashtable<String, ImageIcon>();
	/**
	 * Precompiled pattern for searching line breaks in a string.
	 */
	private static final Pattern TOOLTIP_PATTERN = Pattern.compile("\\n");

	/**
	 * Create a chartPanel with a box layout with the specified orientation.
	 * @param orientation the box orientation, one of {@link javax.swing.BoxLayout#Y_AXIS BoxLayout.Y_AXIS} or
	 * {@link javax.swing.BoxLayout#X_AXIS BoxLayout.X_AXIS}.
	 * @return a <code>JPanel</code> instance.
	 */
	public static JPanel createBoxPanel(int orientation)
	{
		JPanel panel = new JPanel();
		panel.setLayout(new BoxLayout(panel, orientation));
		return panel;
	}

	/**
	 * Load and cache an icon from the file system or classpath.
	 * @param path the path to the icon.
	 * @return the loaded icon as an <code>ImageIcon</code> instance, or null if the icon
	 * could not be loaded.
	 */
	public static ImageIcon loadIcon(String path)
	{
		return loadIcon(path, true);
	}

	/**
	 * Load and cache an icon from the file system or classpath.
	 * @param path - the path to the icon.
	 * @param useCache - specifiies whether the icon should be retrieved from and/or put in the icon cache.
	 * @return the loaded icon as an <code>ImageIcon</code> instance, or null if the icon
	 * could not be loaded.
	 */
	public static ImageIcon loadIcon(String path, boolean useCache)
	{
		ImageIcon icon = null;
		if (useCache)
		{
			icon = iconMap.get(path);
			if (icon != null) return icon;
		}
		URL url = GuiUtils.class.getResource(path);
		if (url == null) return null;
		icon = new ImageIcon(url);
		if (useCache) iconMap.put(path, icon);
		return icon;
	}

	/**
	 * Create a filler component with the specified fixed size. The resulting component can be used as a
	 * separator for layout purposes.
	 * @param width the component's width.
	 * @param height the component's height.
	 * @return a <code>JComponent</code> instance.
	 */
	public static JComponent createFiller(int width, int height)
	{
		JPanel filler = new JPanel();
		Dimension d = new Dimension(width, height);
		filler.setMinimumSize(d);
		filler.setMaximumSize(d);
		filler.setPreferredSize(d);
		return filler;
	}

	/**
	 * Format a possibly multi-line text into a a string that can be properly displayed as a tooltip..
	 * @param tooltip the non-formatted text of the tooltip.
	 * @return the input text if it does not contain any line break, otherwise the input text wrapped in
	 * &lt;html&gt; ... &lt;/html&gt; tags, with the line breaks transformed into &lt;br&gt; tags.
	 */
	public static String formatToolTipText(String tooltip)
	{
		if (tooltip == null) return null;
		String s = TOOLTIP_PATTERN.matcher(tooltip).replaceAll("<br>");
		return "<html>" + s + "</html>";
	}
}

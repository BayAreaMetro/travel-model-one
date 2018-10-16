/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.ui.swing;

import java.awt.Point;
import javax.swing.JScrollPane;
import javax.swing.JViewport;
import javax.swing.SwingUtilities;
import javax.swing.event.ChangeListener;
import javax.swing.event.ChangeEvent;
import java.beans.PropertyChangeListener;
import java.beans.PropertyChangeEvent;

import java.io.Serializable;
import java.io.ObjectOutputStream;
import java.io.ObjectInputStream;
import java.io.IOException;

/**
 * Adjusts the way the JScrollPane component handles scrolling.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class JScrollPaneAdjuster
    implements PropertyChangeListener, Serializable
{
    private JScrollPane pane;

    private transient Adjuster x, y;


    public JScrollPaneAdjuster(JScrollPane pane)
    {
        this.pane = pane;

        this.x = new Adjuster(pane.getViewport(), pane.getColumnHeader(), Adjuster.X);
        this.y = new Adjuster(pane.getViewport(), pane.getRowHeader(), Adjuster.Y);

        pane.addPropertyChangeListener(this);
    }


    public void dispose()
    {
        x.dispose();
        y.dispose();

        pane.removePropertyChangeListener(this);
        pane = null;
    }


    public void propertyChange(PropertyChangeEvent e)
    {
        String name = e.getPropertyName();

        if (name.equals("viewport"))
        {
            x.setViewport((JViewport)e.getNewValue());
            y.setViewport((JViewport)e.getNewValue());
        }
        else if (name.equals("rowHeader"))
        {
            y.setHeader((JViewport)e.getNewValue());
        }
        else if (name.equals("columnHeader"))
        {
            x.setHeader((JViewport)e.getNewValue());
        }
    }


    private void readObject(ObjectInputStream in)
        throws IOException, ClassNotFoundException
    {
        in.defaultReadObject();

        x = new Adjuster(pane.getViewport(), pane.getColumnHeader(), Adjuster.X);
        y = new Adjuster(pane.getViewport(), pane.getRowHeader(), Adjuster.Y);
    }


    private static class Adjuster
        implements ChangeListener, Runnable
    {
        public static final int X = 1, Y = 2;

        private JViewport viewport, header;
        private int type;


        public Adjuster(JViewport viewport, JViewport header, int type)
        {
            this.viewport = viewport;
            this.header = header;
            this.type = type;

            if (header != null)
                header.addChangeListener(this);
        }

        public void setViewport(JViewport newViewport)
        {
            viewport = newViewport;
        }

        public void setHeader(JViewport newHeader)
        {
            if (header != null)
                header.removeChangeListener(this);

            header = newHeader;
            
            if (header != null)
                header.addChangeListener(this);
        }

        public void stateChanged(ChangeEvent e)
        {
            if (viewport == null || header == null)
                return;

            if (type == X)
            {
                if (viewport.getViewPosition().x != header.getViewPosition().x)
                    SwingUtilities.invokeLater(this);
            }
            else
            {
                if (viewport.getViewPosition().y != header.getViewPosition().y)
                    SwingUtilities.invokeLater(this);
            }
        }
        
        public void run()
        {
            if (viewport == null || header == null)
                return;


            Point v = viewport.getViewPosition(),
                h = header.getViewPosition();

            if (type == X)
            {
                if (v.x != h.x)
                    viewport.setViewPosition(new Point(h.x, v.y));
            }
            else
            {
                if (v.y != h.y)
                    viewport.setViewPosition(new Point(v.x, h.y));
            }
        }

        public void dispose()
        {
            if (header != null)
                header.removeChangeListener(this);

            viewport = header = null;
        }
    }
}
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
package org.jppf.ui.monitoring.charts;

import static org.jppf.utils.ReflectionHelper.*;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Paint;
import java.awt.Stroke;
import java.lang.reflect.Proxy;
import java.util.List;
import java.util.Map;

import org.jppf.ui.monitoring.charts.PlotXYChartHandler.LegendLabelGeneratorInvocationHandler;
import org.jppf.ui.monitoring.charts.config.ChartConfiguration;
import org.jppf.ui.monitoring.data.Fields;
import org.jppf.ui.monitoring.data.StatsHandler;

/**
 * Instances of this class are used to create and update line charts with an horizontal orientation.
 * @author Laurent Cohen
 */
public class DifferenceChartHandler implements ChartHandler
{
	/**
	 * The stats formatter that provides the data.
	 */
	private StatsHandler statsHandler = null;

	/**
	 * Initialize this chart handler with a specified stats formatter.
	 * @param statsHandler the stats formatter that provides the data.
	 */
	public DifferenceChartHandler(StatsHandler statsHandler)
	{
		this.statsHandler = statsHandler;
	}

	/**
	 * Create a plot XY chart based on a chart configuration.
	 * @param config holds the configuration parameters for the chart created, modified by this method.
	 * @return a <code>ChartConfiguration</code> instance.
	 * @see org.jppf.ui.monitoring.charts.ChartHandler#createChart(org.jppf.ui.monitoring.charts.config.ChartConfiguration)
	 */
	public ChartConfiguration createChart(ChartConfiguration config)
	{
		Object ds = createDataset(config);
		String s = config.name;
		if (config.unit != null) s += " ("+config.unit+")";
		//JFreeChart chart = ChartFactory.createXYLineChart(s, null, null, ds, PlotOrientation.VERTICAL, true, true, false);
		Object chart = invokeMethod(getClass0("org.jfree.chart.ChartFactory"), null, "createXYLineChart",
			s, null, null, ds, getField(getClass0("org.jfree.chart.plot.PlotOrientation"), null, "VERTICAL"), true, true, false);
		//XYPlot plot = chart.getXYPlot();
		Object plot = invokeMethod(getClass0("org.jfree.chart.JFreeChart"), chart, "getXYPlot");
		//XYDifferenceRenderer rend = new XYDifferenceRenderer(Color.green, Color.red, false);
		Object rend = invokeConstructor(getClass0("org.jfree.chart.renderer.xy.XYDifferenceRenderer"),
			new Class[] {Paint.class, Paint.class, Boolean.TYPE}, Color.green, Color.red, false);
		//plot.setRenderer(rend);
		invokeMethod(plot.getClass(), plot, "setRenderer", new Class[] {getClass0("org.jfree.chart.renderer.xy.XYItemRenderer")}, rend);
		//rend.setBaseSeriesVisibleInLegend(true);
		invokeMethod(rend.getClass(), rend, "setBaseSeriesVisibleInLegend", new Class[] {Boolean.TYPE}, true);
		//rend.setLegendItemLabelGenerator(new LegendLabelGenerator());
		Object labelGenerator = Proxy.newProxyInstance(
			getCurrentClassLoader(), getClasses("org.jfree.chart.labels.XYSeriesLabelGenerator"), new LegendLabelGeneratorInvocationHandler());
		invokeMethod(rend.getClass(), rend, "setLegendItemLabelGenerator", labelGenerator);
		//rend.setBaseStroke(new BasicStroke(2f));
		invokeMethod(rend.getClass(), rend, "setBaseStroke", new Class[] {Stroke.class}, new BasicStroke(2f));
		config.chart = chart;
		return config;
	}

	/**
	 * Create and populate a dataset with the values of the specified fields.
	 * @param config the names of the fields whose values populate the dataset.
	 * @return a <code>DefaultCategoryDataset</code> instance.
	 */
	private Object createDataset(ChartConfiguration config)
	{
		//XYSeriesCollection ds = new XYSeriesCollection();
		Object ds = newInstance("org.jfree.data.xy.XYSeriesCollection");
		if ((config.fields != null) && (config.fields.length >= 2))
		{
			for (int i=0; i<2; i++)
			{
				Fields key = config.fields[i];
				//XYSeries series = new XYSeries(key);
				Object series = invokeConstructor(getClass0("org.jfree.data.xy.XYSeries"), new Class[] {Comparable.class}, key);
				//ds.addSeries(series);
				invokeMethod(ds.getClass(), ds, "addSeries", series);
				//series.setMaximumItemCount(statsHandler.getRolloverPosition());
				invokeMethod(series.getClass(), series, "setMaximumItemCount", statsHandler.getRolloverPosition());
			}
		}
		config.dataset = ds;
		populateDataset(config);
		return ds;
	}
	
	/**
	 * Populate a dataset based on a chart configuration.
	 * @param config the chart configuration containing the dataset to populate.
	 * @return a <code>ChartConfiguration</code> instance.
	 * @see org.jppf.ui.monitoring.charts.ChartHandler#populateDataset(org.jppf.ui.monitoring.charts.config.ChartConfiguration)
	 */
	public ChartConfiguration populateDataset(ChartConfiguration config)
	{
		if (config.fields == null) return config;
		int len = config.fields.length;
		if (len < 2) return config;
		Object ds = config.dataset;
		//List list = ds.getSeries();
		List list = (List) invokeMethod(ds.getClass(), ds, "getSeries");
		for (Object o: list)
		{
			//((XYSeries) o).clear();
			invokeMethod(o.getClass(), o, "clear");
		}
		for (int i=0; i<2; i++)
		{
			Fields key = config.fields[i];
			//XYSeries series = ds.getSeries(i);
			Object series = invokeMethod(ds.getClass(), ds, "getSeries", new Class[] {Integer.TYPE}, i);
			int start = Math.max(0, statsHandler.getTickCount() - statsHandler.getStatsCount());
			for (int j=0; j<statsHandler.getStatsCount(); j++)
			{
				Map<Fields, Double> valueMap = statsHandler.getDoubleValues(j);
				//series.add(start + j, valueMap.get(key));
				invokeMethod(series.getClass(), series, "add", new Class[] { Double.TYPE, Number.class}, start + j, valueMap.get(key));
			}
		}
		return config;
	}

	/**
	 * Update a dataset based on a chart configuration.
	 * @param config the chart configuration containing the dataset to update.
	 * @return a <code>ChartConfiguration</code> instance.
	 * @see org.jppf.ui.monitoring.charts.ChartHandler#updateDataset(org.jppf.ui.monitoring.charts.config.ChartConfiguration)
	 */
	public ChartConfiguration updateDataset(ChartConfiguration config)
	{
		Object ds = config.dataset;
		Map<Fields, Double> valueMap = statsHandler.getLatestDoubleValues();
		if (valueMap != null)
		{
			//for (int i=0; i<ds.getSeriesCount(); i++)
			for (int i=0; i<(Integer) invokeMethod(ds.getClass(), ds, "getSeriesCount"); i++)
			{
				//XYSeries series = ds.getSeries(i);
				Object series = invokeMethod(ds.getClass(), ds, "getSeries", new Class[] {Integer.TYPE}, i);
				//Fields key = (Fields) series.getKey();
				Fields key = (Fields) invokeMethod(series.getClass(), series, "getKey");
				//series.add(statsHandler.getTickCount(), valueMap.get(key));
				invokeMethod(series.getClass(), series, "add", new Class[] { Double.TYPE, Number.class}, statsHandler.getTickCount(), valueMap.get(key));
			}
		}
		return config;
	}
}

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
package sample.datasize;

import java.util.*;
import java.util.concurrent.Future;

import org.jppf.client.*;
import org.jppf.client.concurrent.*;
import org.jppf.server.protocol.JPPFTask;
import org.jppf.utils.*;
import org.slf4j.*;

/**
 * Runner class for the matrix multiplication demo.
 * @author Laurent Cohen
 */
public class DataSizeRunner
{
	/**
	 * Logger for this class.
	 */
	static Logger log = LoggerFactory.getLogger(DataSizeRunner.class);
	/**
	 * JPPF client used to submit execution requests.
	 */
	private static JPPFClient jppfClient = null;
	/**
	 * One kilobyte.
	 */
	private static final int KILO = 1024;
	/**
	 * One kilobyte.
	 */
	private static final int MEGA = 1024 * KILO;

	/**
	 * Entry point for this class, performs a matrix multiplication a number of times.,<br>
	 * The number of times is specified as a configuration property named &quot;matrix.iterations&quot;.<br>
	 * The size of the matrices is specified as a configuration property named &quot;matrix.size&quot;.<br>
	 * @param args not used.
	 */
	public static void main(String...args)
	{
		try
		{
			//jppfClient = new JPPFClient();
			//perform();
			//perform2();
			perform3();
		}
		catch(Exception e)
		{
			e.printStackTrace();
		}
		finally
		{
			if (jppfClient != null) jppfClient.close();
		}
	}
	
	/**
	 * Perform the test.
	 * @throws Exception if an error is raised during the execution.
	 */
	private static void perform() throws Exception
	{
		TypedProperties config = JPPFConfiguration.getProperties();
		boolean inNodeOnly = config.getBoolean("datasize.inNodeOnly", false);
		int datasize = config.getInt("datasize.size", 1);
		int nbTasks = config.getInt("datasize.nbTasks", 10);
		String unit = config.getString("datasize.unit", "b").toLowerCase();
		if ("k".equals(unit)) datasize *= KILO;
		else if ("m".equals(unit)) datasize *= MEGA;
		
		output("Running datasize demo with data size = " + datasize + " with " + nbTasks + " tasks");
		long totalTime = System.currentTimeMillis();
		JPPFJob job = new JPPFJob();
		for (int i=0; i<nbTasks; i++) job.addTask(new DataTask(datasize, inNodeOnly));
		List<JPPFTask> results = jppfClient.submit(job);
		for (JPPFTask t: results)
		{
			if (t.getException() != null) System.out.println("task error: " +  t.getException().getMessage());
			else System.out.println("task result: " + t.getResult());
		}
		totalTime = System.currentTimeMillis() - totalTime;
		output("Computation time: " + StringUtils.toStringDuration(totalTime));
	}

	/**
	 * Perform the test.
	 * @throws Exception if an error is raised during the execution.
	 */
	private static void perform2() throws Exception
	{
		TypedProperties config = JPPFConfiguration.getProperties();
		boolean inNodeOnly = config.getBoolean("datasize.inNodeOnly", false);
		int datasize = config.getInt("datasize.size", 1);
		int nbTasks = config.getInt("datasize.nbTasks", 10);
		String unit = config.getString("datasize.unit", "b").toLowerCase();
		if ("k".equals(unit)) datasize *= KILO;
		else if ("m".equals(unit)) datasize *= MEGA;
		
		JPPFExecutorService executor = new JPPFExecutorService(jppfClient);
		executor.setBatchSize(100);
		executor.setBatchTimeout(30L);
		
		output("Running datasize demo with data size = " + datasize + " with " + nbTasks + " tasks");
		long totalTime = System.currentTimeMillis();
		List<Future<?>> futureList = new ArrayList<Future<?>>();
		for (int i=0; i<nbTasks; i++) futureList.add(executor.submit(new DataTask(datasize, inNodeOnly)));
		for (Future<?> f: futureList)
		{
			f.get();
			JPPFTask t = ((JPPFTaskFuture<?>) f).getTask(); 
			if (t.getException() != null) System.out.println("task error: " +  t.getException().getMessage());
			else System.out.println("task result: " + t.getResult());
		}
		totalTime = System.currentTimeMillis() - totalTime;
		output("Computation time: " + StringUtils.toStringDuration(totalTime));
		executor.shutdownNow();
	}

	/**
	 * Perform the test.
	 * @throws Exception if an error is raised during the execution.
	 */
	private static void perform3() throws Exception
	{
		TypedProperties config = JPPFConfiguration.getProperties();
		int iterations = config.getInt("datasize.iterations", 1);
		output("Running test for " + iterations + " iterations");
		long totalTime = System.currentTimeMillis();
		for (int n=1; n<=iterations; n++)
		{
			jppfClient = new JPPFClient();
			JPPFJob job = new JPPFJob();
			job.setId("job " + n);
			job.addTask(new DataTask(10, true));
			List<JPPFTask> results = jppfClient.submit(job);
			if (n % 1000 == 0) output("executed " + n + " jobs");
			jppfClient.close();
		}
		totalTime = System.currentTimeMillis() - totalTime;
		output("Computation time: " + StringUtils.toStringDuration(totalTime));
	}

	/**
	 * Print a message to the console and/or log file.
	 * @param message the message to print.
	 */
	private static void output(String message)
	{
		System.out.println(message);
		log.info(message);
	}
}

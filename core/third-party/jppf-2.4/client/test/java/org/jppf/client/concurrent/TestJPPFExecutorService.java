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

package org.jppf.client.concurrent;

import static org.junit.Assert.*;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.*;

import org.jppf.test.setup.*;
import org.junit.*;

/**
 * Unit tests for {@link JPPFExecutorService}.
 * @author Laurent Cohen
 */
public class TestJPPFExecutorService extends Setup1D1N1C
{
	/**
	 * Default duration for tasks that use a duration. Adjust the value for slow hardware.
	 */
	protected static final long TASK_DURATION = 1000L;
	/**
	 * The executor we are testing.
	 */
	private ExecutorService executor = null;

	/**
	 * Launches a driver and node and start the client.
	 * @throws IOException if a process could not be started.
	 */
	@Before
	public void setupTest() throws IOException
	{
		executor = new JPPFExecutorService(client);
	}

	/**
	 * Stops the driver and node and close the client.
	 * @throws IOException if a process could not be stopped.
	 */
	@After
	public void cleanupTest() throws IOException
	{
		if ((executor != null) && !executor.isShutdown()) executor.shutdownNow();
	}

	/**
	 * Invocation of <code>JPPFExecutorService.submit(Runnable)</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testSubmitRunnable() throws Exception
	{
		Result result = new Result();
		SimpleRunnable sr = new SimpleRunnable(result);
		Future<?> future = executor.submit(sr);
		future.get();
		assertTrue(future.isDone());
		assertFalse(future.isCancelled());
	}

	/**
	 * Invocation of <code>JPPFExecutorService.submit(Runnable, T)</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testSubmitRunnableWithResult() throws Exception
	{
		Result result = new Result();
		SimpleRunnable sr = new SimpleRunnable(result);
		Future<Result> future = executor.submit(sr, result);
		assertNotNull(future);
		Result finalResult = future.get();
		assertTrue(future.isDone());
		assertFalse(future.isCancelled());
		assertNotNull(finalResult);
		assertEquals(BaseSetup.EXECUTION_SUCCESSFUL_MESSAGE, finalResult.message);
	}

	/**
	 * Invocation of <code>JPPFExecutorService.submit(Callable)</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testSubmitCallable() throws Exception
	{
		SimpleCallable sc = new SimpleCallable();
		Future<Result> future = executor.submit(sc);
		assertNotNull(future);
		Result finalResult = future.get();
		assertTrue(future.isDone());
		assertFalse(future.isCancelled());
		assertNotNull(finalResult);
		assertEquals(BaseSetup.EXECUTION_SUCCESSFUL_MESSAGE, finalResult.message);
	}

	/**
	 * Invocation of <code>JPPFExecutorService.invokdeAll(List&lt;Callable&gt;)</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testInvokeAll() throws Exception
	{
		int n = 10;
		List<SimpleCallable> tasks = new ArrayList<SimpleCallable>();
		for (int i=0; i<n; i++) tasks.add(new SimpleCallable(i));
		List<Future<Result>> futures = executor.invokeAll(tasks);
		assertNotNull(futures);
		assertEquals(n, futures.size());
		for (int i=0; i<n; i++)
		{
			Future<Result> future = futures.get(i);
			assertNotNull(future);
			Result finalResult = future.get();
			assertTrue(future.isDone());
			assertFalse(future.isCancelled());
			assertNotNull(finalResult);
			assertEquals(BaseSetup.EXECUTION_SUCCESSFUL_MESSAGE, finalResult.message);
			assertEquals(i, finalResult.position);
		}
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.invokeAll(List&lt;Callable&gt;, long, TimeUnit)</code>.
	 * In this test, no task has enough time to execute.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testInvokeAllWithTimeout() throws Exception
	{
		int n = 3;
		long timeout = TASK_DURATION / 2L;
		List<SimpleCallable> tasks = new ArrayList<SimpleCallable>();
		for (int i=0; i<n; i++) tasks.add(new SimpleCallable(i, TASK_DURATION));
		List<Future<Result>> futures = executor.invokeAll(tasks, timeout, TimeUnit.MILLISECONDS);
		assertNotNull(futures);
		assertEquals(n, futures.size());
		for (Future<Result> f: futures)
		{
			assertNull(f.get());
			assertTrue(f.isDone());
			assertTrue(f.isCancelled());
		}
		Thread.sleep(100L + (n * TASK_DURATION) - timeout);
	}

	/**
	 * Invocation of <code>JPPFExecutorService.invokdeAny(List&lt;Callable&gt;)</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testInvokeAny() throws Exception
	{
		int n = 10;
		List<SimpleCallable> tasks = new ArrayList<SimpleCallable>();
		for (int i=0; i<n; i++) tasks.add(new SimpleCallable(i));
		Result result = executor.invokeAny(tasks);
		assertNotNull(result);
		assertEquals(BaseSetup.EXECUTION_SUCCESSFUL_MESSAGE, result.message);
		assertTrue(result.position >= 0);
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.invokeAny(List&lt;Callable&gt;, long, TimeUnit)</code>.
	 * In this test, no task has enough time to complete its execution.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testInvokeAnyWithTimeout() throws Exception
	{
		int n = 3;
		long timeout = TASK_DURATION / 2L;
		List<SimpleCallable> tasks = new ArrayList<SimpleCallable>();
		for (int i=0; i<n; i++) tasks.add(new SimpleCallable(i, TASK_DURATION));
		Result result = executor.invokeAny(tasks, timeout, TimeUnit.MILLISECONDS);
		assertNull(result);
		Thread.sleep(100L + (n * TASK_DURATION) - timeout);
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.shutdown()</code>.
	 * In this test, we verify that submitting a task after a shutdown is requested raises a {@link RejectedExecutionException}.
	 * @throws Exception if any error occurs
	 */
	@Test(expected = RejectedExecutionException.class)
	public void testShutdown() throws Exception
	{
		executor.shutdown();
		assertTrue(executor.isShutdown());
		assertTrue(executor.isTerminated());
		executor.submit(new SimpleRunnable());
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.shutdownNow()</code>.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testShutdownNow() throws Exception
	{
		executor.submit(new SimpleRunnable());
		List<Runnable> res = executor.shutdownNow();
		assertTrue(executor.isShutdown());
		assertTrue(executor.isTerminated());
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.awaitTermination(long, TimeUnit)</code>.
	 * In this test, the termination occurs before the timeout expires.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testAwaitTermination() throws Exception
	{
		executor.submit(new SimpleCallable(0, TASK_DURATION));
		executor.shutdown();
		assertTrue(executor.awaitTermination(3L*TASK_DURATION/2L, TimeUnit.MILLISECONDS));
		assertTrue(executor.isShutdown());
		assertTrue(executor.isTerminated());
	}

	/**
	 * Test invocation of <code>JPPFExecutorService.awaitTermination(long, TimeUnit)</code>.
	 * In this test, the timeout expires before the termination occurs.
	 * @throws Exception if any error occurs
	 */
	@Test
	public void testAwaitTermination2() throws Exception
	{
		executor.submit(new SimpleCallable(0, TASK_DURATION));
		Thread.sleep(100L);
		executor.shutdown();
		assertFalse(executor.awaitTermination(TASK_DURATION/2L, TimeUnit.MILLISECONDS));
		assertTrue(executor.isShutdown());
		assertFalse(executor.isTerminated());
	}
}

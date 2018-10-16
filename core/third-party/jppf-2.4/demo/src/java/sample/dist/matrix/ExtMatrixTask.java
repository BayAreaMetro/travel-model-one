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
package sample.dist.matrix;

import sample.BaseDemoTask;

/**
 * This task performs the multiplication of one or more matrixs rows by another matrix, as part of
 * the multiplication of 2 whole square matrices.
 * @author Laurent Cohen
 */
public class ExtMatrixTask extends BaseDemoTask
{
	/**
	 * Data provider key mapping to the second matrix operand in the multiplication.
	 */
	public static final String DATA_KEY = "matrix";
	/**
	 * The row of values to multiply by a matrix.
	 */
	private double[][] rowValues = null;

	/**
	 * Initialize this task with a specified row of values to multiply.
	 * @param rowValues the values as an array of <code>double</code> values.
	 */
	public ExtMatrixTask(double[][] rowValues)
	{
		this.rowValues = rowValues;
	}
	
	/**
	 * Perform the multiplication of a matrix row by another matrix.
	 * @see sample.BaseDemoTask#doWork()
	 */
	public void doWork()
	{
		try
		{
			final Matrix matrix = (Matrix) getDataProvider().getValue(DATA_KEY);
			final int size = matrix.getSize();
			final double[][] computeResult = new double[rowValues.length][size];
	
			// for each row of matrix a
			for (int n=0; n<rowValues.length; n++)
			{
				// for each column of matrix b
				for (int col=0; col<size; col++)
				{
					double sum = 0d;
					for (int row=0; row<size; row++)
					{
						sum += matrix.getValueAt(row, col) * rowValues[n][row];
						//matrix.valueAt(row, col);
					}
					computeResult[n][col] = sum;
				}
			}
			/*
			for (int n=0; n<rowValues.length; n++)
			{
				double count = 0d;
				for (int i=0; i<size; i++)
				{
					for (int j=0; j<size; j++)
					{
						count += 1d;
					}
					computeResult[n][i] = count;
				}
			}
			*/
			/*
			long stop = System.currentTimeMillis() + 5L;
			long count = 0L;
			while (System.currentTimeMillis() < stop) count++;
			*/
			setResult(computeResult);
		}
		catch(Exception e)
		{
			setException(e);
		}
	}
}

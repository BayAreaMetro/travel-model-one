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
package com.pb.common.math.tests;
/* All code Copyright 2004 Christopher W. Cowell-Shah */

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Date;

import com.pb.common.math.MathNative;

public class Benchmark
{
	static long startTime;
	static long stopTime;
	static long elapsedTime;

	public static void main(String[] args)
	{
		int intMax = 		1000000000; // 1B
		double doubleMin = 	1000000000.0; // 10B
		double doubleMax = 	1100000000.0; // 11B
		long longMin = 		1000000000L; // 1B
		long longMax = 		1100000000L; // 1.1B
		double trigMax = 	10000000.0; // 10M
		int ioMax =			1000000; // 1M

		System.out.println("Start Java benchmark");

		long intArithmeticTime = intArithmetic(intMax);
		long doubleArithmeticTime = doubleArithmetic(doubleMin, doubleMax);
		long longCountTime = longArithmetic(longMin, longMax);
		long trigTime = trig(trigMax);
		long ioTime = io(ioMax);
		long totalTime = intArithmeticTime + doubleArithmeticTime +
			longCountTime + trigTime + ioTime;

		System.out.println("Total Java benchmark time: " + totalTime + " ms");
		System.out.println("End Java benchmark");
	}


	/**
	 * Math benchmark using ints.
	 */
	static long intArithmetic(int intMax)
	{
		startTime = (new Date()).getTime();

		int intResult = 1;
		int i = 1;
		while (i < intMax)
		{
			intResult -= (i++)*2;
			intResult += (i++)*5;
			intResult /= (i++)/1;
			intResult *= (i++)/3;
		}

		stopTime = (new Date()).getTime();
		elapsedTime = stopTime - startTime;

		System.out.println("Int arithmetic elapsed time: " + elapsedTime +
			" ms with max of " + intMax);
		System.out.println(" i: " + i + "\n" + " intResult: " + intResult);
		return elapsedTime;
	}


	/**
	 * Math benchmark using doubles.
	 */
	static long doubleArithmetic(double doubleMin, double doubleMax)
	{
		startTime = (new Date()).getTime();

		double doubleResult = doubleMin;
		double i = doubleMin;
		while (i < doubleMax)
		{
			doubleResult -= (i++)*2;
			doubleResult += (i++)*5;
			doubleResult /= (i++)/1;
			doubleResult *= (i++)/3;
		}

		stopTime = (new Date()).getTime();
		elapsedTime = stopTime - startTime;

		System.out.println("Double arithmetic elapsed time: " + elapsedTime +
			" ms with min of " + doubleMin + ", max of " + doubleMax);
		System.out.println(" i: " + i + "\n" + " doubleResult: " + doubleResult);
		return elapsedTime;
	}


	/**
	 * Math benchmark using longs.
	 */
	static long longArithmetic(long longMin, long longMax)
	{
		startTime = (new Date()).getTime();

		long longResult = longMin;
		long i = longMin;
		while (i < longMax)
		{
			longResult -= (i++)*2;
			longResult += (i++)*5;
			longResult /= (i++)/1;
			longResult *= (i++)/3;
		}

		stopTime = (new Date()).getTime();
		elapsedTime = stopTime - startTime;

		System.out.println("Long arithmetic elapsed time: " + elapsedTime +
			" ms with min of " + longMin + ", max of " + longMax);
		System.out.println(" i: " + i);
		System.out.println(" longResult: " + longResult);
		return elapsedTime;
	}


	/**
	 * Calculate sin, cos, tan, log, square root
	 * for all numbers up to a max.
	 */
	static long trig(double trigMax)
	{
		startTime = (new Date()).getTime();

		double sine = 0.0;
		double cosine = 0.0;
		double tangent = 0.0;
		double logarithm = 0.0;
		double exponent = 0.0;
		double squareRoot = 0.0;
		double i = 1.0001;
		while (i < trigMax)
		{
//			sine = JMath.sin(i);
//			cosine = JMath.cos(i);
//			tangent = JMath.tan(i);
			exponent += MathNative.exp((double)i/100000);
			logarithm += MathNative.log((double)i/100000);
//			squareRoot = JMath.sqrt(i);
			i++;
		}

		stopTime = (new Date()).getTime();
		elapsedTime = stopTime - startTime;

		System.out.println("Trig elapsed time: " + elapsedTime +
			" ms with max of " + trigMax);
		System.out.println(" i: " + i);
		System.out.println(" sine: " + sine);
		System.out.println(" cosine: " + cosine);
		System.out.println(" tangent: " + tangent);
		System.out.println(" logarithm: " + logarithm);
		System.out.println(" exponent: " + exponent);
		System.out.println(" squareRoot: " + squareRoot);
		return elapsedTime;
	}


	/**
	 * Write max lines to a file, then read max lines back from file.
	 */
	static long io(int ioMax)
	{
		startTime = (new Date()).getTime();

		final String textLine =
			"abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefgh\n";
		int i = 0;
		String myLine = "";

		try
		{
			File file = new File("C:\\TestJava.txt");
			FileWriter fileWriter = new FileWriter(file);
			BufferedWriter bufferedWriter = new BufferedWriter(fileWriter);
			while (i++ < ioMax)
			{
				bufferedWriter.write(textLine);
			}
			bufferedWriter.close();
			fileWriter.close();

			FileReader inputFileReader = new FileReader(file);
			BufferedReader bufferedReader =
				new BufferedReader(inputFileReader);
			i = 0;
			while (i++ < ioMax)
			{
				myLine = bufferedReader.readLine();
			}
			bufferedReader.close();
			inputFileReader.close();
		}
		catch (IOException e)
		{
			e.printStackTrace();
		}

		stopTime = (new Date()).getTime();
		elapsedTime = stopTime - startTime;
		System.out.println("IO elapsed time: " + elapsedTime +
			" ms with max of " + ioMax);
		System.out.println(" i: " + i);
		System.out.println(" myLine: " + myLine);
		return elapsedTime;
	}
}


package com.pb.common.math.tests;

import junit.framework.TestCase;
import com.pb.common.math.NumericalIntegrator;

public class TestNumericalIntegrator extends TestCase {

	public static void main(String[] args) {
        junit.textui.TestRunner.run(TestNumericalIntegrator.class);
	}

	/*
	 * Test method for 'com.pb.common.math.NumericalIntegrator.Integrate(Function, double, double, double)'
	 */
	public void testIntegrate() {
		NumericalIntegrator.Function myF = new NumericalIntegrator.Function() {

			public double f(double x) {
				return x*2+2;
			}
		};
        
        double result = NumericalIntegrator.Integrate(myF,2,4,1);
        assertTrue("Numerical integration of linear function is not correct", result==16);
		

	}
}

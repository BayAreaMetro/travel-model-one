package com.pb.common.math;

public class NumericalIntegrator {

    public static interface Function {
    	double f(double x);
    }
	static public double Integrate(Function f, double min, double max, double step) {
		int steps = (int) ((max-min)/step);
		if (steps == 0) steps = 1;
		double actualStep = (max-min)/steps;
		double value =0;
		for (int i=0;i<steps;i++) {
			double current = min+(i+0.5)*actualStep;
			value += f.f(current)*actualStep;
		}
		return value;
	}
}

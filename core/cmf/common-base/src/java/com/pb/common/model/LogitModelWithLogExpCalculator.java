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
package com.pb.common.model;

import org.apache.log4j.Logger;

import com.pb.common.math.LogExpCalculator;

/**
 *  The LogitModelWithLogExpCalculator has the same functionality as LogitModel.
 *  The only difference is that it uses LogExpCalculator.exp() instead of MathUtil.exp()
 *  and LogExpCalculator.ln() instead of MathUtil.log().  
 *  
 *  These changes were made in an effort to improve processing time.  It was tested
 *  on a Tucson mode choice application, and compared to using the standard MathUtil
 *  functions.  This took 58:03 for that application, and MathUtil took 56:50.  The
 *  results matched within 50 trips and 0.02%.  
 *
 * @author    Greg Erhardt
 * @version   0.9, 03/02/2006
 */
public class LogitModelWithLogExpCalculator extends LogitModel {
	
	private double precision;
	protected static Logger logger = Logger.getLogger(LogitModelWithLogExpCalculator.class);
	
	public LogitModelWithLogExpCalculator(String n) {
		super(n);
		precision = 0.001; 
	}
	
	public void setPrecision(double p) {
		precision = p; 
	}
	
	/**
    Calculates and returns the composite utility (logsum) for all available
    alternatives in this LogitModel.  This method will exponentiate the utilites,
    but the utilities must be calculated for each alternative prior to calling
    this method.
    @return The composite utility (logsum value) of all the alternatives. If
    this alternative is not available (ie no sub-alterantives are available) the
    return value is 0.
    */
    public double getUtility() throws ModelException {

        double sum = 0;
        double base = 0;

        int i = 0;
        nf.setMaximumFractionDigits(8);
        nf.setMinimumFractionDigits(8);
        for (int alt = 0; alt < alternatives.size(); ++alt) {
            Alternative thisAlt = (Alternative) alternatives.get(alt);
            if (thisAlt.isAvailable()) {
                double utility = thisAlt.getUtility();
                double constant = thisAlt.getConstant();

                //if alternative has a very large negative utility, it isn't available
                if (utility + constant < -400) {
	                expUtilities[i] = 0.0;
	     			++i;           
                    continue;
                }
                setAvailability(true);

                expUtilities[i] = LogExpCalculator.exp(
                		dispersionParameter * (utility + constant), 
                		precision);
                sum += expUtilities[i];
                Boolean elemental = (Boolean) isElementalAlternative.get(i);
                if (elemental.equals(Boolean.TRUE) && debug)
                    logger.info(
                        String.format("%-20s", thisAlt.getName())
                            + "\t\t"
                            + nf.format(utility)
                            + "\t\t\t"
                            + nf.format(constant)
                            + "\t\t\t"
                            + nf.format(expUtilities[i]));
            } else
                expUtilities[i] = 0.0;
            ++i;
        }
        if (isAvailable()) {
            base = (1 / dispersionParameter) * LogExpCalculator.ln(sum, precision);

            if (Double.isNaN(base))
                throw new ModelException(ModelException.INVALID_UTILITY);

            if (debug)
                logger.info(String.format("%-20s", getName()) + "\t\t" + nf.format(base));
            //
            return base;
        }
        return 0.0;
    }

}

package com.pb.models.synpop.test;

import com.pb.common.util.SeededRandom;
import com.pb.models.synpop.SPG;

import org.apache.log4j.Logger;

/**
 * Specify a cumulative probability distribution where the last element is 1.0
 * and test that the correct index values are determined. 
 *
 */
public class TestGetSelectionFromCumProbabilities {
    
	protected static Logger logger = Logger.getLogger(TestGetSelectionFromCumProbabilities.class);
    
    
    public TestGetSelectionFromCumProbabilities() {
    }
    
    private void runTest( SPG testObject, int numElements, double entry ) {
        
        // generate a random cumulative distribution of length numElements
        double[] cumProbDist = getCumulativeProbabilityDistribution( numElements );
        
        // replicate testObject.getSelectionFromCumProbabilities() to test binary search method in that class.
        double randomNumber = entry;
        int index = testObject.binarySearchDouble (cumProbDist, randomNumber);
        
        logger.info ( String.format("\ncumulative distribution generated:") );
        logger.info ( String.format("%-5s  %16s", "i", "cumProbDist[i]") );
        for (int i=0; i < numElements; i++) {
            logger.info( String.format("%-5d  %16.8f", i, cumProbDist[i]) );
        }
        logger.info ( String.format("search for %f returned index %d\n", randomNumber, index) );

    }
    
    
    private double[] getCumulativeProbabilityDistribution (int numElements) {
        
        double[] cumProbabilities = new double[numElements];
        double[] probabilities = new double[numElements];
        double total = 0.0;
        
        // create an array of random numbers and a total of those numbers
        for (int i=0; i < numElements; i++) {
            probabilities[i] = SeededRandom.getRandom();
            total += probabilities[i];
        }

        // divide each random number by total to get a set of proportions that sum to 1
        // also create an array of these cumulative proportions to return
        probabilities[0] /= total;
        cumProbabilities[0] = probabilities[0];
        for (int i=1; i < numElements-1; i++) {
            probabilities[i] /= total;
            cumProbabilities[i] = cumProbabilities[i-1] + probabilities[i];
        }
        cumProbabilities[numElements-1] = 1.0;

        return cumProbabilities;
        
    }
    
    
    // the following main() is used to test the methods implemented in this object.
    public static void main (String[] args) {
        
        TestGetSelectionFromCumProbabilities test = new TestGetSelectionFromCumProbabilities();
        
        // create an SPG object so we can test its getSelectionFromCumProbabilities() method.
        SPG testObject = new SPG();
        
        // call the runTest() method several times
        test.runTest( testObject, 10, 0.3333 );
        test.runTest( testObject, 1, 0.88 );
        test.runTest( testObject, 2, 0.88 );
        test.runTest( testObject, 3, 0.88 );
        test.runTest( testObject, 4, 0.0 );
        test.runTest( testObject, 8, 0.99999 );
        test.runTest( testObject, 8, 1.0 );
        test.runTest( testObject, 6, -0.1 );
        
    }

}




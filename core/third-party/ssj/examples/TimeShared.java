import umontreal.iro.lecuyer.simevents.*;
import umontreal.iro.lecuyer.simprocs.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.randvar.*;
import umontreal.iro.lecuyer.stat.Tally;
import java.io.*;

public class TimeShared {
   int nbTerminal   = 20;    // Number of terminals.
   double quantum;           // Quantum size.
   double overhead  = 0.001; // Amount of overhead (h).
   double meanThink = 5.0;   // Mean thinking time.
   double alpha     = 0.5;   // Parameters of the Weibull service times.
   double lambda    = 1.0;   //               ''
   double delta     = 0.0;   //               ''
   int N            = 1100;  // Total number of tasks to simulate.
   int N0           = 100;   // Number of tasks for warmup.
   int nbTasks;              // Number of tasks ended so far.

   RandomStream streamThink  = new MRG32k3a();
   RandomVariateGen genThink = new ExponentialGen (streamThink, 1.0/meanThink);
   RandomStream streamServ   = new MRG32k3a ("Gen. for service requirements");
   RandomVariateGen genServ = new WeibullGen (streamServ, alpha, lambda, delta);
   Resource server       = new Resource (1, "The server");
   Tally meanInRep       = new Tally ("Average for current run");
   Tally statDiff        = new Tally ("Diff. on mean response times");

   class Terminal extends SimProcess {
      public void actions() {
         double arrivTime;    // Arrival time of current request.
         double timeNeeded;   // Server's time still needed for it.
         while (nbTasks < N) {
            delay (genThink.nextDouble());
            arrivTime = Sim.time();
            timeNeeded = genServ.nextDouble();
            while (timeNeeded > quantum) {
               server.request (1);
               delay (quantum + overhead);
               timeNeeded -= quantum;
               server.release (1);
            }
            server.request (1);  // Here, timeNeeded <= quantum.
            delay (timeNeeded + overhead);
            server.release (1);
            nbTasks++;
            if (nbTasks > N0)
               meanInRep.add (Sim.time() - arrivTime);
                       // Take the observation if warmup is over.
         }
         Sim.stop();            // N tasks have now completed.
      }
   }

   private void simulOneRun() {
      SimProcess.init();
      server.init();
      meanInRep.init();
      nbTasks = 0;
      for (int i=1; i <= nbTerminal; i++)
         new Terminal().schedule (0.0);
      Sim.start();
   }

   // Simulate numRuns pairs of runs and prints a confidence interval
   // on the difference of perf. for quantum sizes q1 and q2.
   public void simulateConfigs (double numRuns, double q1, double q2) {
      double mean1;  // To memorize average for first configuration.
      for (int rep = 0; rep < numRuns; rep++) {
         quantum = q1;
         simulOneRun();
         mean1 = meanInRep.average();
         streamThink.resetStartSubstream();
         streamServ.resetStartSubstream();
         quantum = q2;
         simulOneRun();
         statDiff.add (mean1 - meanInRep.average());
         streamThink.resetNextSubstream();
         streamServ.resetNextSubstream();
      }
      statDiff.setConfidenceIntervalStudent();
      System.out.println (statDiff.report (0.9, 3));
   }

   public static void main (String[] args) { 
      new TimeShared().simulateConfigs (10, 0.1, 0.2);
   }
}

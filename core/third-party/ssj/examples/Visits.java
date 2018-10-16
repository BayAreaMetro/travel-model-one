import umontreal.iro.lecuyer.simevents.*;
import umontreal.iro.lecuyer.simprocs.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.randvar.*;
import umontreal.iro.lecuyer.stat.*;
// import umontreal.iro.lecuyer.simprocs.dsol.SimProcess;

public class Visits {
   int queueSize;    // Size of waiting queue.
   int nbLost;       // Number of visitors lost so far today.
   Bin visitReady = new Bin ("Visit ready"); 
                     // A token becomes available when there 
                     // are enough visitors to start a new visit.
   Tally avLost = new Tally ("Nb. of visitors lost per day"); 
   RandomVariateGen genArriv = new ExponentialGen (new MRG32k3a(), 20.0);
                                               // Interarriv.
   RandomStream  streamSize  = new MRG32k3a(); // Group sizes.
   RandomStream  streamBalk  = new MRG32k3a(); // Balking decisions.
    
   private void oneDay() { 
      queueSize = 0;   nbLost = 0;
      SimProcess.init();
      visitReady.init();
      closing.schedule (16.0);
      new Arrival().schedule (9.75);
      for (int i=1; i<=3; i++) new Guide().schedule (10.0);
      Sim.start();
      avLost.add (nbLost);
   }

   Event closing = new Event() {
      public void actions() {
         if (visitReady.waitList().size() == 0)
            nbLost += queueSize;
         Sim.stop();
      }
   };

   class Guide extends SimProcess {
      public void actions() {
         boolean lunchDone = false;
         while (true) {
            if (Sim.time() > 12.0 && !lunchDone) {
               delay (0.5);  lunchDone = true;
            }
            visitReady.take (1);  // Starts the next visit.
            if (queueSize > 15) queueSize -= 15;
            else queueSize = 0;
            if (queueSize >= 8) visitReady.put (1); 
                                  // Enough people for another visit.
            delay (0.75);
         }
      }
   }
    
   class Arrival extends SimProcess {
      public void actions() {
         while (true) {
            delay (genArriv.nextDouble());
            // A new group of visitors arrives.
            int groupSize;  // number of visitors in group.
            double u = streamSize.nextDouble();
            if (u <= 0.2)      groupSize = 1;
            else if (u <= 0.8) groupSize = 2;
            else if (u <= 0.9) groupSize = 3;
            else               groupSize = 4;
            if (!balk()) {
               queueSize += groupSize;
               if (queueSize >= 8 &&
                   visitReady.getAvailable() == 0)
                  // A token is now available.
                  visitReady.put (1);
               }
            else  nbLost += groupSize;
         }
      }
     
      private boolean balk() {
         if (queueSize <= 10)  return false;
         if (queueSize >= 40)  return true;
         return (streamBalk.nextDouble() < 
	 ((queueSize - 10.0) / 30.0));
      }
   }

   public void simulateRuns (int numRuns) {
      for (int i = 1; i <= numRuns; i++) oneDay();
      avLost.setConfidenceIntervalStudent();
      System.out.println (avLost.report (0.9, 3));
   }

   static public void main (String[] args) { 
      new Visits().simulateRuns (100);
   }    
}

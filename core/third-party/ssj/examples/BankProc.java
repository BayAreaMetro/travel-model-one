import umontreal.iro.lecuyer.simprocs.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.randvar.*;
import umontreal.iro.lecuyer.stat.*;

public class BankProc {

   ProcessSimulator sim = new ThreadProcessSimulator();
   double   minute = 1.0 / 60.0;
   int      nbServed;           // Number of customers served so far
   double   meanDelay;          // Mean time between arrivals
   SimProcess  nextCust;        // Next customer to arrive
   Resource tellers         = new Resource (sim, 0, "The tellers");
   RandomStream  streamArr  = new MRG32k3a(); // Customer's arrivals
   ErlangGen genServ        = new ErlangConvolutionGen
                                    (new MRG32k3a(), 2, 1.0/minute);
   RandomStream  streamTeller  = new MRG32k3a(); // Number of tellers
   RandomStream  streamBalk    = new MRG32k3a(); // Balking decisions
   Tally    statServed    = new Tally ("Nb. served per day");
   Tally    avWait        = new Tally ("Average wait per day (hours)");

   class OneDay extends SimProcess {
      public OneDay(ProcessSimulator sim) { super(sim); }
      public void actions() {
         int nbTellers;         // Number of tellers today.
         nbServed = 0;
         tellers.setCapacity (0);
         tellers.waitList().initStat();
         meanDelay = 2.0 * minute;
         // It is 9:45, start arrival process.
         (nextCust = new Customer(sim)).schedule
           (ExponentialGen.nextDouble (streamArr, 1.0/meanDelay));
         delay (15.0 * minute);
         // Bank opens at 10:00, generate number of tellers.
         double u = streamTeller.nextDouble();
         if (u >= 0.2) nbTellers = 3;
         else if (u < 0.05)  nbTellers = 1;
         else nbTellers = 2;
         tellers.setCapacity (nbTellers);
         delay (1.0);   // It is 11:00, double arrival rate.
         nextCust.reschedule (nextCust.getDelay() / 2.0);
         meanDelay = minute;
         delay (3.0);   // It is 14:00, halve arrival rate.
         nextCust.reschedule (nextCust.getDelay() * 2.0);
         meanDelay = 2.0 * minute;
         delay (1.0);   // It is 15:00, bank closes.
         nextCust.cancel();
      }
   }

   class Customer extends SimProcess {
      public Customer(ProcessSimulator sim) { super(sim); }
      public void actions() {
         (nextCust = new Customer(sim)).schedule
            (ExponentialGen.nextDouble (streamArr, 1.0/meanDelay));
         if (!balk()) {
            tellers.request (1);
            delay (genServ.nextDouble());
            tellers.release (1);
            nbServed++;
         }
      }

      private boolean balk() {
         int n = tellers.waitList().size();
         return n > 9 || (n > 5 && 5.0*streamBalk.nextDouble() < n - 5);
      }
   }

   public void simulOneDay() { 
      sim.init();
      new OneDay(sim).schedule (9.75);
      sim.start();
      statServed.add (nbServed);
      avWait.add (tellers.waitList().statSize().sum());
   }

   public void simulateDays (int numDays) {
      tellers.waitList().setStatCollecting (true);
      for (int i=1; i<=numDays; i++)  simulOneDay();
      System.out.println (statServed.report());
      System.out.println (avWait.report());
   }

   public static void main (String[] args) { 
       new BankProc().simulateDays (100);
   }
}

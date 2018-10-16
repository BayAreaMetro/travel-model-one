import umontreal.iro.lecuyer.simevents.*;
import umontreal.iro.lecuyer.simprocs.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.randvar.ExponentialGen;
import umontreal.iro.lecuyer.stat.Tally;
import java.io.*;
import java.util.*;

public class Jobshop {
   int nbMachTypes;       // Number of machine types M.
   int nbTaskTypes;       // Number of task types N.
   double warmupTime;     // Warmup time T_0.
   double horizonTime;    // Horizon length T.
   boolean warmupDone;    // Becomes true when warmup time is over.
   Resource[] machType;   // The machines groups as resources.
   TaskType[] taskType;   // The task types.
   RandomStream streamArr = new MRG32k3a(); // Stream for arrivals.
   BufferedReader input;

   public Jobshop() throws IOException { readData(); }

   // Reads data file, and creates machine types and task types.
   void readData() throws IOException {
      input = new BufferedReader (new FileReader ("Jobshop.dat"));
      StringTokenizer line = new StringTokenizer (input.readLine());
      warmupTime = Double.parseDouble (line.nextToken());
      line = new StringTokenizer (input.readLine());
      horizonTime = Double.parseDouble (line.nextToken());
      line = new StringTokenizer (input.readLine());
      nbMachTypes = Integer.parseInt (line.nextToken());
      nbTaskTypes = Integer.parseInt (line.nextToken());
      machType = new Resource[nbMachTypes];
      for (int m=0; m < nbMachTypes; m++) {
         line = new StringTokenizer (input.readLine());
         String name = line.nextToken();
         int nb = Integer.parseInt (line.nextToken());
         machType[m] = new Resource (nb, name);
      }
      taskType = new TaskType[nbTaskTypes];
      for (int n=0; n < nbTaskTypes; n++)
         taskType[n] = new TaskType();
      input.close();
   }


   class TaskType {
      public String     name;        // Task name.
      public double     arrivalRate; // Arrival rate.
      public int        nbOper;      // Number of operations.
      public Resource[] machOper;    // Machines where operations occur.
      public double[]   lengthOper;  // Durations of operations.
      public Tally      statSojourn; // Stats on sojourn times.

      // Reads data for new task type and creates data structures.
      TaskType() throws IOException {
         StringTokenizer line = new StringTokenizer (input.readLine());
         statSojourn = new Tally (name = line.nextToken()); 
         arrivalRate = Double.parseDouble (line.nextToken());
         nbOper = Integer.parseInt (line.nextToken());
         machOper = new Resource[nbOper];
         lengthOper = new double[nbOper];
         for (int i = 0; i < nbOper; i++) {
            int p = Integer.parseInt (line.nextToken());
            machOper[i] = machType[p-1];
            lengthOper[i] = Double.parseDouble (line.nextToken());
         }
      }

      // Performs the operations of this task (to be called by a process).
      public void performTask (SimProcess p) {
         double arrivalTime = Sim.time();
         for (int i=0; i < nbOper; i++) {
            machOper[i].request (1); p.delay (lengthOper[i]);
            machOper[i].release (1);
         }
         if (warmupDone) statSojourn.add (Sim.time() - arrivalTime);
      }
   }

   public class Task extends SimProcess {
      TaskType type;

      Task (TaskType type) { this.type = type; }

      public void actions() { 
	  // First schedules next task of this type, then executes task.
         new Task (type).schedule (ExponentialGen.nextDouble
               (streamArr, type.arrivalRate));
         type.performTask (this);
      }
   }

   Event endWarmup = new Event() {
      public void actions() {
         for (int m=0; m < nbMachTypes; m++)
            machType[m].setStatCollecting (true);
         warmupDone = true;
      }
   };

   Event endOfSim = new Event() {
      public void actions() { Sim.stop(); }
   };

   public void simulateOneRun() {
      SimProcess.init();
      endOfSim.schedule (horizonTime);
      endWarmup.schedule (warmupTime);
      warmupDone = false;
      for (int n = 0; n < nbTaskTypes; n++) {
         new Task (taskType[n]).schedule (ExponentialGen.nextDouble 
            (streamArr, taskType[n].arrivalRate));
      }
      Sim.start();
   }

   public void printReportOneRun() {
      for (int m=0; m < nbMachTypes; m++) 
         System.out.println (machType[m].report());
      for (int n=0; n < nbTaskTypes; n++) 
         System.out.println (taskType[n].statSojourn.report());
   }

   static public void main (String[] args) throws IOException { 
      Jobshop shop = new Jobshop();
      shop.simulateOneRun();
      shop.printReportOneRun();
   }
}

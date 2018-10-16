import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.hups.*;
import umontreal.iro.lecuyer.stat.Tally;
import umontreal.iro.lecuyer.util.Chrono;

public class AsianQMCk extends AsianQMC {

   public AsianQMCk (double r, double sigma, double strike,
                     double s0, int s, double[] zeta) {
       super (r, sigma, strike, s0, s, zeta);
   }

   // Makes m independent randomizations of the digital net p using stream
   // noise. For each of them, performs one simulation run for each point
   // of p, and adds the average over these points to the collector statQMC.
   public void simulateQMC (int m, PointSet p,
                            RandomStream noise, Tally statQMC) {
      Tally statValue  = new Tally ("stat on value of Asian option");
      PointSetIterator stream = p.iterator ();
      for (int j=0; j<m; j++) {
          p.randomize (noise);
          stream.resetStartStream();
          simulateRuns (p.getNumPoints(), stream, statValue);
          statQMC.add (statValue.average());
      }
   }


   public static void main (String[] args) {
      int s = 12;
      double[] zeta = new double[s+1];
      for (int j=0; j<=s; j++)
         zeta[j] = (double)j / (double)s;
      AsianQMCk process = new AsianQMCk (0.05, 0.5, 100.0, 100.0, s, zeta);
      Tally statValue  = new Tally ("value of Asian option");
      Tally statQMC = new Tally ("QMC averages for Asian option");

      Chrono timer = new Chrono();
      int n = 100000;
      System.out.println ("Ordinary MC:\n");
      process.simulateRuns (n, new MRG32k3a(), statValue);
      statValue.setConfidenceIntervalStudent();
      System.out.println (statValue.report (0.95, 3));
      System.out.println ("Total CPU time: " + timer.format());
      double varMC = statValue.variance();
      double cpuMC = timer.getSeconds() / n;  // CPU seconds per run.
      System.out.println ("------------------------\n");

      timer.init();
      KorobovLattice p = new KorobovLattice (65521, 944, s); // approx. 2^{16} points.
      BakerTransformedPointSet pb = new BakerTransformedPointSet (p);

      n = p.getNumPoints();
      int m = 20;                     // Number of QMC randomizations.
      process.simulateQMC (m, pb, new MRG32k3a(), statQMC);
      System.out.println ("QMC with Korobov point set with " + n +
          " points and random shift + baker:\n");
      statQMC.setConfidenceIntervalStudent();
      System.out.println (statQMC.report (0.95, 3));
      System.out.println ("Total CPU time: " + timer.format() + "\n");
      double varQMC = p.getNumPoints() * statQMC.variance();
      double cpuQMC = timer.getSeconds() / (m * n);
      System.out.printf ("Variance ratio:   %9.4g%n", varMC/varQMC);
      System.out.printf ("Efficiency ratio: %9.4g%n",
           (varMC * cpuMC) / (varQMC * cpuQMC));
   }
}

import java.util.Observer;
import java.util.Observable;
import java.awt.*;
import java.awt.event.*;
import javax.swing.*;
import umontreal.iro.lecuyer.stat.*;
import umontreal.iro.lecuyer.simevents.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.probdist.ExponentialDist;
import umontreal.iro.lecuyer.randvar.RandomVariateGen;

public class QueueObs2 {
   static final double meanArr  = 10.0;
   static final double meanServ =  9.0;
   static final int numCust     = 50000;

   RandomVariateGen genArr   = new RandomVariateGen
               (new MRG32k3a(), new ExponentialDist (1.0/meanArr));
   RandomVariateGen genServ  = new RandomVariateGen
               (new MRG32k3a(), new ExponentialDist (1.0/meanServ));
   Tally waitingTime = new Tally
      ("Customers waiting time");
 
   public static void main (String[] args) { 
      QueueObs2 qb = new QueueObs2();
      SpyWindow sw = new SpyWindow (qb);
      qb.waitingTime.setBroadcasting (true);
      qb.waitingTime.addObservationListener (sw);
      sw.pack();
      sw.setVisible(true);
      qb.simulation();
      System.out.println (qb.waitingTime.report());
      System.exit (0);
   }

   public void simulation() {
      double Wi = 0.0;
      waitingTime.add (Wi);
      for (int i = 2; i <= numCust; i++) {
         Wi += genServ.nextDouble() - genArr.nextDouble();
         if (Wi < 0.0)
            Wi = 0.0;
         waitingTime.add (Wi);
      }
   }
}

class SpyWindow extends JFrame implements ObservationListener {
   private int nObs = 0;
   private JTextArea obs = new JTextArea (25, 80);
   private JScrollPane sp = new JScrollPane (obs);
   private QueueObs2 qb;

   public SpyWindow (QueueObs2 qb) {
      super ("Observation spy");
      this.qb = qb;
      sp.getViewport().setScrollMode (JViewport.BACKINGSTORE_SCROLL_MODE);
      setContentPane (sp);
      setDefaultCloseOperation (WindowConstants.DO_NOTHING_ON_CLOSE);
      addWindowListener (new WindowClose());
   }

   public void newObservation (StatProbe probe, double x) {
      Rectangle vrect = sp.getViewport().getViewRect();
      Dimension vsize = sp.getViewport().getViewSize();
      boolean rescroll = vrect.y+vrect.height == vsize.height;
      obs.append
	 ("Customer " + (nObs++) + " waited " + x + " minutes.\n");
      synchronized (sp) {
	 JViewport vp = sp.getViewport();
	 vsize = vp.getViewSize();
	 vp.scrollRectToVisible
	    (new Rectangle (0, vsize.height - 15, vsize.width, vsize.height));
      }
   }

   class WindowClose extends WindowAdapter {
      public void windowClosing (WindowEvent ev) {
	 qb.waitingTime.removeObservationListener (SpyWindow.this);
	 dispose();
      }
   }
}

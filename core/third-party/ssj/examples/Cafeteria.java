import umontreal.iro.lecuyer.simevents.*;
import umontreal.iro.lecuyer.simprocs.*;
import umontreal.iro.lecuyer.rng.*;
import umontreal.iro.lecuyer.randvar.*;
import umontreal.iro.lecuyer.stat.Tally;

/**
 * This example simulates the Cafeteria from
 * A. M. Law and W. D. Kelton, Simulation Modeling and Analysis,
 * Second Edition, McGraw-Hill, New York, 1991,
 * exercise 2.30, p. 224.
 */
public class Cafeteria {
    static final int Hotfood  = 0;
    static final int Sandwich = 1;
    static final int Drinks   = 2;    
    static final double minHotST  = 50.0; static final double maxHotST  = 120.0;
    static final double minSandST = 60.0; static final double maxSandST = 180.0;
    static final double minDrinkST = 5.0; static final double maxDrinkST = 20.0;
    static final double minHotACT = 20.0; static final double maxHotACT  = 40.0;
    static final double minSandACT = 5.0; static final double maxSandACT = 15.0;
    static final double minDrinkACT= 5.0; static final double maxDrinkACT= 10.0;
    static final double meanArr = 30.0;

    int NbCaisses;               // Nb de caisses.                 
    double  Nb;                  // Nb de clients dans le systeme. 
    int NbAttente = 0;           // Nb. en attente pour caisses.
    double NbHot, NbSand;        // Nb. serveurs au HotFood et aux Sandwichs.

    RandomStream streamArr = new MRG32k3a(), streamGrSize     = new MRG32k3a(),
        streamRoute     = new MRG32k3a(),    streamHotServ    = new MRG32k3a(),
        streamSandServ  = new MRG32k3a(),    streamDrinksServ = new MRG32k3a(),
        streamHotACT    = new MRG32k3a(),    streamSandACT    = new MRG32k3a(),
        streamDrinksACT = new MRG32k3a();          
    RandomVariateGen genArr = new ExponentialGen (streamArr, 1.0/meanArr);

    Resource HotServ = new Resource(1,"Service repas chauds");
    Resource SandServ = new Resource(1,"Service sandwich");
    Resource Caisse[] = new Resource[3];

    Accumulate NbClients = new Accumulate ("Nb. de clients dans le systeme");
    Accumulate CaissesNb = new Accumulate ("Nb. en attente pour les caisses");
    Tally CaissesAttente = new Tally ("Temps d'attente pour caisses"); 
    Tally AttClient[] = new Tally[3];   // Temps d'attente, par type de client.

    class  ProcGenArr extends SimProcess {
	    // Processus de generation des arrivees des clients.               
       public void actions() {
          double u;
          while (true){
             delay (genArr.nextDouble());
             u = streamGrSize.nextDouble();
             new ProcClient().schedule (0.0);
             if (u > 0.5) new ProcClient().schedule (0.0);
             if (u > 0.8) new ProcClient().schedule (0.0);
             if (u > 0.9) new ProcClient().schedule (0.0);
          }
       }   
    }

    class ProcClient extends SimProcess {
	// Comportement d'un client.
	double u, ACT, TArr, Attente;
	int T;      //    Type de client

	public void actions() {
	   Nb += 1.0;   NbClients.update(Nb);   TArr = Sim.time();
	   u = streamRoute.nextDouble();
	   if (u < 0.8) {
		T = Hotfood;
		HotServ.request(1);    Attente = Sim.time() - TArr;
		delay (UniformGen.nextDouble (streamHotServ, minHotST/NbHot, 
					  maxHotST/NbHot));
		HotServ.release (1);
		ACT = UniformGen.nextDouble (streamHotACT, minHotACT, maxHotACT);
	    }
	    else if ( u < 0.95) {
		T = Sandwich;
		SandServ.request (1);   Attente = Sim.time() - TArr;
		delay (UniformGen.nextDouble (streamSandServ, minSandST/NbSand, 
					  maxSandST/NbSand));
		SandServ.release (1);
		ACT = UniformGen.nextDouble (streamSandACT, minSandACT, maxSandACT);
	    }
	    else T = Drinks;
	    delay (UniformGen.nextDouble (streamDrinksServ, minDrinkST, maxDrinkST));
	    ACT += UniformGen.nextDouble (streamDrinksACT, minDrinkACT, maxDrinkACT);
	    int c = 0;                  // c sera la caisse choisie.  
	    for (int i=1;  i<NbCaisses;  i++) { 
		if (Caisse [i].waitList().size() < 
		    Caisse [c].waitList().size())  c = i;
	    }
	    TArr = Sim.time(); 
	    CaissesNb.update (++NbAttente);
	    Caisse[c].request (1);
	    CaissesNb.update (--NbAttente);
	    AttClient [T].add (Attente + Sim.time() - TArr);
	    CaissesAttente.add (Sim.time() - TArr);
	    delay (ACT);
	    Caisse[c].release (1);
	    Nb -= 1.0;   NbClients.update (Nb);
	}
    }
     
    class ProcFinSim extends Event {
	public void actions(){
	    System.out.println(HotServ.report());      
            System.out.println(SandServ.report()); 
            System.out.println(CaissesNb.report()); 
            System.out.println(CaissesAttente.report());
	    System.out.println(NbClients.report());    
            System.out.println(AttClient[Hotfood].report());	    
	    System.out.println(AttClient [Sandwich].report());  
            System.out.println(AttClient [Drinks].report());
	    System.out.print ("\nAttente moyenne globale: "+ 
			     (0.80 * AttClient [Hotfood].average() 
	     	            + 0.15 * AttClient [Sandwich].average() 
			    + 0.05 * AttClient [Drinks].average() )+"\n\n");
	    Sim.stop();
            System.out.print ("==========================================\n");
	}
    }

    public void SimCafeteria (int Ncais, double Nhot, double Nsand ){
	System.out.print (Ncais+" caisses, "+(int)Nhot+" aux repas chauds et "+
			 (int)Nsand+" aux sandwichs\n");
        NbCaisses = Ncais;  NbHot=Nhot;  NbSand=Nsand;
        Nb = 0.0;  NbAttente=0;
	SimProcess.init();
	HotServ.init();	 SandServ.init();  NbClients.init(); 
	CaissesNb.init(); CaissesAttente.init();
	for (int i=0; i<3; i++) { Caisse[i].init();  AttClient[i].init(); }
	new ProcFinSim().schedule (4500.0); // On va simuler 4500 secondes. 
	new ProcGenArr().schedule (0.0);
	Sim.start();
    }

    public Cafeteria(){
	AttClient[Hotfood]  = new Tally("Temps d'attente repas chauds");
	AttClient[Sandwich] = new Tally("Temps d'attente sandwich");
	AttClient[Drinks]   = new Tally("Temps d'attente breuvages");
	for (int i=0; i<3; i++) {
	    Caisse[i] = new Resource (1, "Une caisse");
	    Caisse[i].setStatCollecting (true);
	}
	HotServ.setStatCollecting (true);
	SandServ.setStatCollecting (true);
	SimCafeteria (2, 1.0, 1.0); 
	SimCafeteria (3, 1.0, 1.0); 
	SimCafeteria (2, 2.0, 1.0); 
	SimCafeteria (2, 1.0, 2.0); 
	SimCafeteria (2, 2.0, 2.0); 
	SimCafeteria (3, 2.0, 1.0); 
	SimCafeteria (3, 1.0, 2.0); 
	SimCafeteria (3, 2.0, 2.0); 
    }

    public static void main (String[] args) {new Cafeteria();}

}

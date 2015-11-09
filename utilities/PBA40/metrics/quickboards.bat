:: Batch file to run quickboards transit summary program
:: Software written by tad/billy, SFCTA
:: Modified by gde, PB
::
::Usage:\nquickboards  ctlfile  [outfile]
::Control file keywords:
::NodesFile=  [f:\\champ\\util\\nodes.xls] path of nodes.xls lookup file
::TimePeriods=[am,md,pm,ev,ea] list of time periods to analyze
::LineStats=  [t|f] true/false to create summary stats for all lines
::Lines=      [] csv list of TP+ line names for station-level boardings
::Stations=   [] csv list of TP+ nodes for detailed boardings by line
::Paths=      [] csv list of five-letter codes of transit dbf's to load (nswtw,nswta,nsatw,sfwlw,sfabw,sfapw,sfwba,sfwbw,sfwmw,sfwpa,sfwpw,viswmw)
::Summary=    [t|f] true/false to generate line-level summary (true)\

@echo off
java -Xms64m -Xmx512m -cp CTRAMP\runtime\quickboards.jar org.sfcta.quickboards.QuickBoards %1 %2

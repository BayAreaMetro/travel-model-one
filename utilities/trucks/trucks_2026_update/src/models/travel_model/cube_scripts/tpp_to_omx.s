; Convert truck OD matrices from CUBE's .tpp format to .omx, so they're
; readable in Python. One CONVERTMAT block per .tpp file.
;
; TEMPLATE — fill in the real .tpp filenames/paths your model run produces
; (check hwy\ or wherever RunIteration.bat writes outputs), one CONVERTMAT block
; per file (no loop construct — list them all out). Run with cwd set to the
; scenario root, so the paths below are relative to it.

RUN PGM=MATRIX

CONVERTMAT  FILEI="nonres/TruckTG.dat",
            FILEO="nonres/TruckTG.omx",
            FORMAT=TPP, OFORMAT=OMX

ENDRUN

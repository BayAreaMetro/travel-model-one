# Code Arterial Tollclasses.r
# Script to code arterial tollclass values based on parallel freeways
# SI

# Set working directory

directory <- "L:/Application/Model_One/NextGenFwys/NetworkProject_Development/Arterials"

# Import libraries

library(pacman)
p_load(tidyverse,foreign)

# Set up input and output directories
#arterial_in     <- file.path(directory,"Shapefile","2035 with Tollclass Updates and Arterial Links.dbf")
#match_in        <- file.path(directory,"Shapefile","Arterial_parallels.dbf")
match_in        <- file.path(directory,"Shapefile","arterial_parallelness_no_FT_1.dbf")
tollclass_in    <- file.path(directory,"Shapefile","2035 with Tollclass Updates.dbf")
node_in         <- file.path(directory,"Shapefile","2035 Nodes.dbf")
  
# Bring in DBF files
   
#arterial  <- read.dbf(arterial_in)
match     <- read.dbf(match_in) %>% select(A_Art=A,B_Art=B,matchFwy_C) %>% 
  separate(.,col=matchFwy_C,into=c("A_Fwy","B_Fwy"),sep="-") %>% 
  mutate(A_Fwy=as.integer(A_Fwy),B_Fwy=as.integer(B_Fwy))
tollclass <- read.dbf(tollclass_in) %>% select(A,B,ROUTENUM,ROUTEDIR,TOLLCLASS,FT)
node      <- read.dbf(node_in) %>% select(N,X,Y)

# Join together equivalencies, calculate bearing from x,y values

match1 <- left_join(match,tollclass,by=c("A_Fwy"="A","B_Fwy"="B")) %>% 
  left_join(.,node,by=c("A_Art"="N")) %>% rename(A_Art_X=X,A_Art_Y=Y) %>% 
  left_join(.,node,by=c("B_Art"="N")) %>% rename(B_Art_X=X,B_Art_Y=Y) %>% 
  left_join(.,node,by=c("A_Fwy"="N")) %>% rename(A_Fwy_X=X,A_Fwy_Y=Y) %>% 
  left_join(.,node,by=c("B_Fwy"="N")) %>% rename(B_Fwy_X=X,B_Fwy_Y=Y) %>% 
  mutate(Fwy_E_W=if_else(B_Fwy_X-A_Fwy_X>0,"E","W"),
         Fwy_N_S=if_else(B_Fwy_Y-A_Fwy_Y>0,"N","S"),
         Art_E_W=if_else(B_Art_X-A_Art_X>0,"E","W"),
         Art_N_S=if_else(B_Art_Y-A_Art_Y>0,"N","S"),
         Orientation=case_when(
           ROUTEDIR %in% c("N","S")   ~ "N_S",
           ROUTEDIR %in% c("E","W")   ~ "E_W",
           TRUE                       ~ "None"))

# Write out csv to manually enter ROUTEDIR and Orientation for missing values, then re-import
# Create alternate tollclass for links that run in opposite direction of matched tollclass link

write.csv(match1,file.path(directory,"match1.csv"),row.names = FALSE)
match2 <- read.csv(file.path(directory,"match1_fixed.csv"), header = TRUE) %>% 
  mutate(TOLLCLASS_ALT=case_when(
    TOLLCLASS==          990401          ~     990402,
    TOLLCLASS==          990402          ~     990401,
    TOLLCLASS==          990403          ~     990404,
    TOLLCLASS==          990404          ~     990403,
    TOLLCLASS==          990407          ~     990408,
    TOLLCLASS==          990408          ~     990407,
    TOLLCLASS==          990172          ~     990171,
    TOLLCLASS==          990241          ~     990242,
    TOLLCLASS==          990242          ~     990241,
    TOLLCLASS==          990243          ~     990244,
    TOLLCLASS==          990075          ~     990076,
    TOLLCLASS==          990076          ~     990075,
    TOLLCLASS==          990077          ~     990078,
    TOLLCLASS==          990078          ~     990077,
    TOLLCLASS==          990081          ~     990082,
    TOLLCLASS==          990082          ~     990081,
    TOLLCLASS==          990083          ~     990084,
    TOLLCLASS==          990084          ~     990083,
    TOLLCLASS==          990085          ~     990086,
    TOLLCLASS==          990086          ~     990085,
    TOLLCLASS==          990087          ~     990088,
    TOLLCLASS==          990088          ~     990087,
    TOLLCLASS==          990091          ~     990092,
    TOLLCLASS==          990092          ~     990091,
    TOLLCLASS==          990853          ~     990854,
    TOLLCLASS==          990854          ~     990853,
    TOLLCLASS==          990855          ~     990856,
    TOLLCLASS==          990856          ~     990855,
    TOLLCLASS==          990871          ~     990872,
    TOLLCLASS==          990872          ~     990871,
    TOLLCLASS==          990923          ~     990924,
    TOLLCLASS==          990924          ~     990923,
    TOLLCLASS==          990927          ~     990928,
    TOLLCLASS==          990928          ~     990927,
    TOLLCLASS==          990101          ~     990102,
    TOLLCLASS==          990102          ~     990101,
    TOLLCLASS==          990103          ~     990104,
    TOLLCLASS==          990104          ~     990103,
    TOLLCLASS==          990105          ~     990106,
    TOLLCLASS==          990106          ~     990105,
    TOLLCLASS==          990107          ~     990108,
    TOLLCLASS==          990108          ~     990107,
    TOLLCLASS==          990109          ~     990110,
    TOLLCLASS==          990110          ~     990109,
    TOLLCLASS==          990111          ~     990112,
    TOLLCLASS==          990112          ~     990111,
    TOLLCLASS==          990113          ~     990114,
    TOLLCLASS==          990114          ~     990113,
    TOLLCLASS==          990115          ~     990116,
    TOLLCLASS==          990116          ~     990115,
    TOLLCLASS==          990117          ~     990118,
    TOLLCLASS==          990118          ~     990117,
    TOLLCLASS==          990119          ~     990120,
    TOLLCLASS==          990120          ~     990119,
    TOLLCLASS==          990122          ~     990121,
    TOLLCLASS==          990123          ~     990124,
    TOLLCLASS==          990124          ~     990123,
    TOLLCLASS==          990136          ~     990135,
    TOLLCLASS==          990231          ~     990232,
    TOLLCLASS==          990232          ~     990231,
    TOLLCLASS==          990233          ~     990234,
    TOLLCLASS==          990234          ~     990233,
    TOLLCLASS==          990239          ~     990240,
    TOLLCLASS==          990240          ~     990239,
    TOLLCLASS==          990245          ~     990246,
    TOLLCLASS==          990281          ~     990282,
    TOLLCLASS==          990282          ~     990281,
    TOLLCLASS==          990283          ~     990284,
    TOLLCLASS==          990285          ~     990286,
    TOLLCLASS==          990286          ~     990285,
    TOLLCLASS==          990287          ~     990288,
    TOLLCLASS==          990288          ~     990287,
    TOLLCLASS==          990289          ~     990290,
    TOLLCLASS==          990290          ~     990289,
    TOLLCLASS==          990691          ~     990692,
    TOLLCLASS==          990692          ~     990691,
    TOLLCLASS==          990381          ~     990382,
    TOLLCLASS==          990382          ~     990381,
    TOLLCLASS==          990581          ~     990582,
    TOLLCLASS==          990582          ~     990581,
    TOLLCLASS==          990583          ~     990584,
    TOLLCLASS==          990584          ~     990583,
    TOLLCLASS==          990585          ~     990586,
    TOLLCLASS==          990586          ~     990585,
    TOLLCLASS==          990587          ~     990588,
    TOLLCLASS==          990588          ~     990587,
    TOLLCLASS==          990590          ~     990589,
    TOLLCLASS==          990683          ~     990684,
    TOLLCLASS==          990684          ~     990683,
    TOLLCLASS==          990689          ~     990690,
    TOLLCLASS==          990690          ~     990689,
    TOLLCLASS==          990691          ~     990692,
    TOLLCLASS==          990692          ~     990691,
    TOLLCLASS==          990879          ~     990880,
    TOLLCLASS==          990880          ~     990879,
    TOLLCLASS==          990881          ~     990882,
    TOLLCLASS==          990882          ~     990881,
    TOLLCLASS==          990883          ~     990884,
    TOLLCLASS==          990884          ~     990883,
    TOLLCLASS==          990885          ~     990886,
    TOLLCLASS==          990886          ~     990885,
    TOLLCLASS==          990887          ~     990888,
    TOLLCLASS==          990888          ~     990887,
    TOLLCLASS==          990889          ~     990890,
    TOLLCLASS==          990890          ~     990889,
    TOLLCLASS==          990891          ~     990892,
    TOLLCLASS==          990892          ~     990891,
    TOLLCLASS==          990981          ~     990982,
    TOLLCLASS==          990982          ~     990981,
    TRUE                                ~     -9999)
  ) %>% relocate(.,TOLLCLASS_ALT,.after=TOLLCLASS)

# Code freeway tollclass values

miscode= 999999

match3 <- match2 %>% mutate(
  TOLLCLASS=as.numeric(TOLLCLASS),
  interim_tollclass=case_when(
    (Fwy_E_W=="W" & Fwy_N_S=="S" & Art_E_W=="E" & Art_N_S=="N") ~ TOLLCLASS_ALT,
    (Fwy_E_W=="W" & Fwy_N_S=="S" & Art_E_W=="W" & Art_N_S=="S") ~ TOLLCLASS,
    (Fwy_E_W=="E" & Fwy_N_S=="N" & Art_E_W=="W" & Art_N_S=="S") ~ TOLLCLASS_ALT,
    (Fwy_E_W=="E" & Fwy_N_S=="S" & Art_E_W=="E" & Art_N_S=="S") ~ TOLLCLASS,
    (Fwy_E_W=="E" & Fwy_N_S=="S" & Art_E_W=="W" & Art_N_S=="S") ~ miscode,
    (Fwy_E_W=="E" & Fwy_N_S=="S" & Art_E_W=="W" & Art_N_S=="N") ~ TOLLCLASS_ALT,
    (Fwy_E_W=="W" & Fwy_N_S=="N" & Art_E_W=="E" & Art_N_S=="S") ~ TOLLCLASS_ALT,
    (Fwy_E_W=="W" & Fwy_N_S=="N" & Art_E_W=="W" & Art_N_S=="S") ~ miscode,
    (Fwy_E_W=="W" & Fwy_N_S=="N" & Art_E_W=="E" & Art_N_S=="N") ~ miscode,
    (Fwy_E_W=="E" & Fwy_N_S=="N" & Art_E_W=="E" & Art_N_S=="N") ~ TOLLCLASS,
    (Fwy_E_W=="W" & Fwy_N_S=="N" & Art_E_W=="W" & Art_N_S=="N") ~ TOLLCLASS,
    (Fwy_E_W=="E" & Fwy_N_S=="S" & Art_E_W=="E" & Art_N_S=="N") ~ miscode,
    (Fwy_E_W=="E" & Fwy_N_S=="N" & Art_E_W=="E" & Art_N_S=="S") ~ miscode,
    (Fwy_E_W=="E" & Fwy_N_S=="N" & Art_E_W=="W" & Art_N_S=="N") ~ miscode,
    (Fwy_E_W=="W" & Fwy_N_S=="S" & Art_E_W=="W" & Art_N_S=="N") ~ miscode,
    (Fwy_E_W=="W" & Fwy_N_S=="S" & Art_E_W=="E" & Art_N_S=="S") ~ miscode)
) %>% 
  relocate(.,c(Fwy_E_W,Fwy_N_S),.after = Art_N_S)


-----------------

# Break apart arterials and freeway links and then rematch by directionality, find outliers
art_break <- match2 %>% 
  select(A_Art, B_Art, A_Fwy, B_Fwy, ROUTENUM, ROUTEDIR, 
         TOLLCLASS, FT, A_Art_X, A_Art_Y, B_Art_X, B_Art_Y, 
         A_Fwy_X, A_Fwy_Y, B_Fwy_X, B_Fwy_Y, Fwy_E_W, Fwy_N_S, 
         Art_E_W, Art_N_S, Orientation)
fwy_break <- match2 %>% 
  select(A_Art, B_Art, A_Fwy, B_Fwy, ROUTENUM, ROUTEDIR, 
         TOLLCLASS, FT, A_Art_X, A_Art_Y, B_Art_X, B_Art_Y, 
         A_Fwy_X, A_Fwy_Y, B_Fwy_X, B_Fwy_Y, Fwy_E_W, Fwy_N_S, 
         Art_E_W, Art_N_S, Orientation)

# Write out shapefile

st_write(just_arterials,'L:/Application/Model_One/NextGenFwys/NetworkProject_Development/Arterials/Shapefile/2035 with Tollclass Updates and Arterial Links.shp')



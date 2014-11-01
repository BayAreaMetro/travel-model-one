# -*- coding: utf-8 -*-
"""
Created on Fri Sep 06 16:28:01 2013

@author: dvauti
"""

annualization = 300
import sys
import csv

# RUN B/C SCRIPTS
#test_mode = raw_input('Enable test shortcut mode? Y or N ')

#if test_mode=='N':
sys.argv = 0    
execfile("baseproj.py")
sys.argv = 1
execfile("baseproj.py")

# IDENTIFY INPUT FILES FOR B/C CALCULATION AND ADD TO ARRAYS
input_file_name = raw_input('Input File Name: ')
input_data = list(csv.reader(open(input_file_name, 'rb')))     

baseline_csv_name = input_data[1][1] + '_step1output.csv'
baseline_txt = list(csv.reader(open(baseline_csv_name, 'rb')))
baseline = [0]*53

project_csv_name = input_data[2][1] + '_step1output.csv'
project_txt = list(csv.reader(open(project_csv_name, 'rb')))
project_id = input_data[2][1]
project = [0]*53

daydiff = [0]*53
anndiff = [0]*53
mondiff = [0]*53

# CALCULATE NOMINAL AND MONETARY BENEFITS

for i in range(49):
    baseline[i]=float(baseline_txt[0][i])
    project[i]=float(project_txt[0][i])
    
for i in range(33):
    daydiff[i]=project[i]-baseline[i]
    anndiff[i]=daydiff[i]*annualization
    
baseline[49]=baseline[18]
baseline[50]=baseline[19]
project[49]=project[18]
project[50]=project[19]

for i in range(44,51):
    daydiff[i]=project[i]-baseline[i]
    
# ovtt adjustment calculation
daydiff[52]=(project[48]-baseline[48])*project[47]

for i in range(44,48):
    anndiff[i]=daydiff[i]
    
for i in range(48,53):
    anndiff[i]=daydiff[i]*annualization

monval = [-16.03,-16.03,-16.03,-26.24,-16.03,-26.24,-16.03,-16.03,-16.03,-16.03,-16.03,
          -35.266,-35.266,-35.266,0,0,-16.03,-16.03,-.2688,-.395,-490300,-487200,-55.35,
          -5700,-12800,-32200,-6400,-5100,-7800,-40500,-4590000,-64000,-2455,
          0,0,0,0,0,0,0,0,0,0,0,-6290,0,1220,0,0,-.0012,-.015,0,-35.266]

for i in range(53):
    mondiff[i]=monval[i]*anndiff[i]
    
# OFF-MODEL MODULES
    
# PARKING CALCULATION
x = .5  # share of parking that occurs at a location's other than at home
k = .5  # share of work-related trips on project route

# parking cost savings calculation
mondiff[51]= -anndiff[15]*x*(project[33]*(7.16*k+5.64*(1-k))+project[34]*(.04*(1-k))+
                            project[35]*(.15*k+.33*(1-k))+project[36]*(.54*k+.39*(1-k)))
                        
  
# TEMP ADJUSTMENT TO REMOVE O&M COSTS (calculate outside of script instead)
zeroOM = raw_input('Enable zeroing out of O&M costs? Y or N ')

if zeroOM == 'Y':
    baseline[18]=0
    baseline[19]=0
    project[18]=0
    project[19]=0
    daydiff[18]=0
    daydiff[19]=0
    anndiff[18]=0
    anndiff[19]=0
    monval[18]=0
    monval[19]=0
    mondiff[18]=0
    mondiff[19]=0
                            
# PROJECT COST INPUTS
                 
                            
capcosts = float(input_data[14][1])
omcosts = float(input_data[15][1])

# improve this with if statements
life = float(input_data[16][1])
box = float(input_data[17][1])

# note that O&M input should be annual, or should be adjusted later
ancapcosts = capcosts/life
anomcosts = (omcosts*(1-box))
totcosts = ancapcosts + anomcosts

bc = sum(mondiff)/(ancapcosts+anomcosts)


# SUMMARY OF RESULTS

print("\n SUMMARY OF RESULTS")
print("\n Auto/Truck Travel Time Benefits (in millions of dollars): ")
tt = sum(mondiff[0:4])
print(round(tt/1000000,1))
nrd = sum(mondiff[4:6])
print("\n Auto/Truck Non-Recurring Delay Benefits (in millions of dollars): ")
print(round(nrd/1000000,1))
ivtt = sum(mondiff[6:11])
print("\n In-Vehicle Transit Travel Time Benefits (in millions of dollars): ")
print(round(ivtt/1000000,1))
ovtt = sum(mondiff[11:14]) + mondiff[52]
print("\n Out-of-Vehicle Transit Travel Time Benefits (in millions of dollars): ")
print(round(ovtt/1000000,1))
wbtt = sum(mondiff[16:18])
print("\n Walk/Bike Travel Time Benefits (in millions of dollars): ")
print(round(wbtt/1000000,1))
opc = sum(mondiff[18:20])
print("\n Auto/Truck Operating Cost Benefits (in millions of dollars): ")
print(round(opc/1000000,1))
print("\n Auto Ownership Cost Benefits (in millions of dollars): ")
print(round(mondiff[44]/1000000,1))
print("\n Auto Parking Cost Benefits (in millions of dollars): ")
print(round(mondiff[50]/1000000,1))
pm = sum(mondiff[20:22])
print("\n Particulate Matter Benefits (in millions of dollars): ")
print(round(pm/1000000,1))
print("\n Carbon Dioxide Benefits (in millions of dollars): ")
print(round(mondiff[22]/1000000,1))
aq = sum(mondiff[23:30])
print("\n Other Air Quality Benefits (in millions of dollars): ")
print(round(aq/1000000,1))
print("\n Collision Fatality Benefits (in millions of dollars): ")
print(round(mondiff[30]/1000000,1))
print("\n Collision Injury Benefits (in millions of dollars): ")
print(round(mondiff[31]/1000000,1))
print("\n Collision Property Damage Benefits (in millions of dollars): ")
print(round(mondiff[32]/1000000,1))
print("\n Physical Activity Benefits (in millions of dollars): ")
print(round(mondiff[46]/1000000,1))
noise = sum(mondiff[49:51])
print("\n Noise Benefits (in millions of dollars): ")
print(round(noise/1000000,1))

print("\n Total Benefits (in millions of dollars): ")
totben = sum(mondiff)
print(round(totben/1000000,1))

print("\n Total Costs (in millions of dollars): ")
print(round(totcosts/1000000,1))

print("\n B/C Ratio: ")
print(round(bc,1))

# temporary testing output
csv_file_name = project_id + '_results.csv'
f = open(csv_file_name,'wt')
writer = csv.writer(f)
csv_output = [baseline, project, daydiff, anndiff, mondiff]
writer.writerows(csv_output)
f.close()


exit
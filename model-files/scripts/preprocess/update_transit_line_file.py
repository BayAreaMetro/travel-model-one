import pandas as pd
import numpy as np
import os

os.chdir("trn")

line_name_list = []
usera1_list = []
usera2_list = []
mode_list = []
faresystem_list = []
operator_list = []
vehicletype_list = []
headway_list = []
headway_type = []
oneway_list = []

with open('transit.lin', 'r') as lines_file:
    for line in lines_file:
        line_name = line.find('LINE NAME')
        usera1 = line.find(' USERA1')
        usera2 = line.find(' USERA2')
        mode = line.find(' MODE')
        faresystem = line.find(' FARESYSTEM')
        operator = line.find(' OPERATOR')
        vehicle_type = line.find(' VEHICLETYPE')
        headway_1 = line.find('HEADWAY')
        oneway = line.find('ONEWAY')
        if line_name != -1:
            value = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            line_name_list.append(value)
        if usera1 != -1:
            value_usera1 = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            usera1_list.append(value_usera1)
        if usera2 != -1:
            value_usera2 = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            usera2_list.append(value_usera2)
        if mode != -1:
            value_mode = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            mode_list.append(value_mode)
        if faresystem != -1:
            value_faresystem = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            faresystem_list.append(value_faresystem)
        if operator != -1:
            value_operator = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            operator_list.append(value_operator)
        if vehicle_type != -1:
            value_vehicle_type = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            vehicletype_list.append(value_vehicle_type)
        if headway_1 != -1:
            value_headway = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            value_headway_type = line.split('=')[0].replace('"', '').replace(
                ',', '').replace('HEADWAY[', '').replace(']', '')
            headway_list.append(value_headway)
            headway_type.append(value_headway_type)
        if oneway == 0:
            value_oneway = line.split('=')[1].replace(
                '"', '').replace(',', '').strip()
            oneway_list.append(value_oneway)

dataframe = {'NAME': line_name_list,
             'USERA1': usera1_list,
             'USERA2': usera2_list,
             'MODE': mode_list,
             'FARESYSTEM': faresystem_list,
             'OPERATOR': operator_list,
             'VEHICLETYPE': vehicletype_list,
             'HEADWAY_TYPE': headway_type,
             'HEADWAY': headway_list,
             #   'HEADWAY_3':headway_3_list,
             #   'HEADWAY_4':headway_4_list
             }
transit_line = pd.DataFrame(dataframe)
transit_line['Name_Characters'] = transit_line['NAME'].apply(lambda x: len(x))

transit_line['agency_id'] = transit_line['NAME'].apply(lambda x: x.split('_')[0])
transit_line['route_id'] = transit_line['NAME'].apply(lambda x: x.split('_')[1][-3:])
transit_line['tme_period'] = transit_line['NAME'].apply(lambda x: x.split('_')[2])
transit_line['direction_id'] = transit_line['NAME'].apply(lambda x: str(x.split('_')[3][1:]))
transit_line['shape_id'] = transit_line['NAME'].apply(lambda x: x.split('_')[4])

# transit_line['new_name'] = np.where(transit_line['Name_Characters']>10,
#                                     transit_line['agency_id']+'_'+transit_line['route_id']+'_'+transit_line['tme_period']+'_'+transit_line['direction_id'][:1],
#                                     transit_line['NAME'][0:10])

transit_line['new_name'] = transit_line['agency_id']+'_'+transit_line['route_id'] + \
    '_'+transit_line['tme_period']+'_'+transit_line['direction_id']

transit_line['FARESYSTEM_NUMERIC']=transit_line['FARESYSTEM'].apply(lambda x: int(x))
transit_line['MODE_NUMERIC'] = transit_line['MODE'].apply(lambda x: int(x))
name_dict = dict(zip(transit_line['NAME'], transit_line['new_name']))

output_file = open('transitUpdated.lin', 'w')

with open('transit.lin', 'r+') as fr, open('transitUpdated.lin', 'r+') as fw:
    
    for line in fr:
        opening_tag = line.find(';;<<PT>><<LINE>>;;')
        line_name = line.find('LINE NAME')
        nntime = line.find('NNTIME=')
        if opening_tag==0:
            fw.write(';;<<Trnbuild>>;;\n\n')
        else: 
            fw.write('\n\nLINE NAME='+name_dict[line.split('=')[1].replace(',', '').replace('"', '').replace('\n', '')]+',\n' if line_name == 0
                    else (line.split(',')[0]+',\n' if nntime == 10
                        else (line.replace('HEADWAY', 'FREQ'))))
            
print('Updating PT Transit Line file to TRNBUILD Line File: Success')

vehtype = pd.read_csv('vehtype.pts', 
                      sep='=', 
                      index_col=False,
                      names=['VEHICLETYPE', 'TYPE', 'SEATCAP', 'CRUSHCAP', 'LOADDISTFAC','CROWDCURVE[1]', 'CROWDCURVE[2]', 'CROWDCURVE[3]'])
vehtype['VEHICLETYPE'] = vehtype['TYPE'].apply(lambda x: x.split(' ')[0])
vehtype['TYPE'] = vehtype['SEATCAP'].apply(lambda x: x[0:-8])
vehtype['SEATCAP'] = vehtype['CRUSHCAP'].apply(lambda x: x.split(' ')[0])
vehtype['CRUSHCAP'] = vehtype['LOADDISTFAC'].apply(lambda x: x.split(' ')[0])
vehtype['LOADDISTFAC'] = vehtype['CROWDCURVE[1]'].apply(lambda x: x.split(' ')[0])

transit_veh = pd.merge(transit_line, 
                       vehtype[['VEHICLETYPE', 'TYPE','SEATCAP', 'CRUSHCAP', 'LOADDISTFAC']],
                       on='VEHICLETYPE',
                       how='left')

transit_veh['Name'] = transit_veh['new_name']
transit_veh['System'] = transit_veh['USERA1']
transit_veh['Stripped'] = transit_veh['USERA2']
transit_veh['Line'] = transit_veh['USERA1']
transit_veh['FullLineName'] = transit_veh['NAME']
transit_veh['AM Vehicle Type'] = transit_veh['TYPE'].apply(lambda x: x.replace('"', ''))
transit_veh['PM Vehicle Type'] = transit_veh['TYPE'].apply(lambda x: x.replace('"', ''))
transit_veh['OP Vehicle Type'] = transit_veh['TYPE'].apply(lambda x: x.replace('"', ''))
transit_veh[['Name', 'System',
             'Stripped', 'Line', 'FullLineName', 'AM Vehicle Type',
             'PM Vehicle Type', 'OP Vehicle Type']].to_csv('transitLineToVehicle.csv', index=False)

trans_prefix = transit_veh[['OPERATOR', 'System', 'AM Vehicle Type']]
trans_prefix = trans_prefix.rename(columns={'Operator': 'Prefix', 
                                            'AM Vehicle Type': 'VehicleType'}).drop_duplicates().to_csv('transitPrefixToVehicle.csv', index=False)

##All vehicle types are included in the transitVehicleToCapacity.csv file already. So not modifying it.




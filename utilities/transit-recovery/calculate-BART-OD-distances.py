USAGE = """
  This script is to calculate the distances between BART stations using
  GTFS data. Used in conjunction with summarize-BART-hourly-ridership.py,
  we can look at BART trip distance distributions change over time.
  
"""
import pathlib
import pandas
import partridge

# this is used to figure out distances between stops
BART_GTFS = pathlib.Path("M:\\Data\\Transit\\511\\2023-08-GTFSTransitData_BA.zip")
# Ouput will be here
OUTPUT_BART_OD_DISTS = BART_GTFS.parents[0] / "2023-08-GTFSTransitData_BA-orig-dest-distances.csv"

def create_transfer_ods(o_d_distances, TRANSFER):
    """ 
    Given a set of od trips in o_d_distances, plus a transfer station,
    makes the list of transfer trip ods and returns it.

    """
    to_transfer   = o_d_distances.loc[o_d_distances.stop_id_B == TRANSFER]
    from_transfer = o_d_distances.loc[o_d_distances.stop_id_A == TRANSFER]
        
    # put them together as cross product
    transfer_trips_df = pandas.merge(
        left  = to_transfer,
        right = from_transfer,
        how   = 'cross',
        suffixes = ['_preXfer', '_postXfer']
    )
    print("transfer_trips_df AT {} len={:,}".format(
        TRANSFER, len(transfer_trips_df)))
    transfer_route_combos = transfer_trips_df[['route_ids_preXfer', 'route_ids_postXfer']].value_counts().reset_index()
    # use these to filter to valid transfers and add below
    print("transfer_route_combos:\n{}".format(transfer_route_combos))
        
    # for DALY, only keep North to North or South to South
    if TRANSFER == 'DALY':
        transfer_trips_df = transfer_trips_df.loc[
            # NB
            ((transfer_trips_df['route_ids_preXfer']=='Red-N,Yellow-N')&
              transfer_trips_df['route_ids_postXfer'].isin(['Green-N','Blue-N','Blue-N,Green-N'])) |
            # SB
            (transfer_trips_df['route_ids_preXfer'].isin(['Green-S','Blue-S','Blue-S,Green-S'])&
             (transfer_trips_df['route_ids_postXfer']=='Red-S,Yellow-S'))
        ]

    elif TRANSFER == 'MCAR':
        transfer_trips_df = transfer_trips_df.loc[
            # NB Orange to Yellow
            ((transfer_trips_df['route_ids_preXfer']=='Orange-N')&
             (transfer_trips_df['route_ids_postXfer']=='Yellow-N')) |
            # SB Yellow to Orange
            ((transfer_trips_df['route_ids_preXfer']=='Yellow-S')&
             (transfer_trips_df['route_ids_postXfer']=='Orange-S')) |
            # U Orange/Red to yellow
            ((transfer_trips_df['route_ids_preXfer']=='Orange-S,Red-S')&
             (transfer_trips_df['route_ids_postXfer']=='Yellow-N')) |
            # U Yellow to Orange/Red
            ((transfer_trips_df['route_ids_preXfer']=='Yellow-S')&
             (transfer_trips_df['route_ids_postXfer']=='Orange-N,Red-N'))
        ]

    elif TRANSFER == 'BAYF':
        transfer_trips_df = transfer_trips_df.loc[
            # U Green/Orange to Blue
            ((transfer_trips_df['route_ids_preXfer']=='Green-S,Orange-N')&
             (transfer_trips_df['route_ids_postXfer']=='Blue-N')) |
            # U Blue to Green/Orange
            ((transfer_trips_df['route_ids_preXfer']=='Blue-S')&
             (transfer_trips_df['route_ids_postXfer']=='Green-N,Orange-S')) |
            # NB Blue to Orange
            ((transfer_trips_df['route_ids_preXfer']=='Blue-S')&
             (transfer_trips_df['route_ids_postXfer']=='Orange-N')) |
            # SB Orange to Blue
            ((transfer_trips_df['route_ids_preXfer']=='Orange-S')&
             (transfer_trips_df['route_ids_postXfer']=='Blue-N'))
        ]
    elif TRANSFER == 'COLS':
        # must be to or from Beige
        transfer_trips_df = transfer_trips_df.loc[
            # from Beige-N
            ((transfer_trips_df['route_ids_preXfer']=='Beige-N')&
             (transfer_trips_df['route_ids_postXfer']!='Beige-S')) |
            # to Beige-S
            ((transfer_trips_df['route_ids_preXfer']!='Beige-N')&
             (transfer_trips_df['route_ids_postXfer']=='Beige-S'))
        ]
    else:
        raise Exception("TRANSFER {} not supported".format(TRANSFER))

    transfer_trips_df['dist'] = transfer_trips_df['dist_preXfer'] + transfer_trips_df['dist_postXfer']
    transfer_trips_df['route_ids'] = transfer_trips_df['route_ids_preXfer'] + ' ' + TRANSFER + \
        ' ' + transfer_trips_df['route_ids_postXfer']
    transfer_trips_df.drop(columns=['stop_id_B_preXfer','dist_preXfer','route_ids_preXfer',
                                    'stop_id_A_postXfer','dist_postXfer','route_ids_postXfer'], inplace=True)
    transfer_trips_df.rename(columns={'stop_id_A_preXfer':'stop_id_A',
                                      'stop_id_B_postXfer':'stop_id_B'}, inplace=True)
    print("transfer_trips_df len={:,} head(30)=\n{}".format(
        len(transfer_trips_df), transfer_trips_df.head(30)))
    return transfer_trips_df

if __name__ == '__main__':
    pandas.set_option("display.max_columns", 40)
    pandas.set_option("display.max_rows", 10000)
    pandas.set_option("display.width",     5000)

    # creating a station-to-station distance dataframe
    print("Reading BART_GTFS")
    feed = partridge.load_feed(BART_GTFS)

    # print(feed.routes)
    # print(feed.trips.head(20))
    # print(feed.stop_times.head(20))

    # get the route_id
    stop_times_df = pandas.merge(
        left=feed.stop_times,
        right=feed.trips[['route_id','trip_id']],
        how="left"
    )

    # groupby route_id, trip_id to count stops
    trips_df = stop_times_df.groupby(by=['route_id','trip_id']).agg(
        num_stops     = pandas.NamedAgg(column='stop_id', aggfunc='count'),
        first_stop_id = pandas.NamedAgg(column='stop_id', aggfunc='first'),
        last_stop_id  = pandas.NamedAgg(column='stop_id', aggfunc='last'),
    ).reset_index()

    # groupby route_id to find longest trip for each route
    routes_max_stops_df = trips_df.groupby(by=['route_id']).agg(
        max_num_stops = pandas.NamedAgg(column='num_stops', aggfunc='max')
    ).reset_index()
    # print(routes_max_stops_df)
    # filter down trips to just those with num_stops = max_num_stops
    trips_df = pandas.merge(
        left=trips_df,
        right=routes_max_stops_df,
        how="left"
    )
    trips_df = trips_df.loc[ trips_df.num_stops == trips_df.max_num_stops ]
    trips_df = trips_df.groupby('route_id').first()
    print("routes: trip_id for longest trips:\n{}".format(trips_df))
    longest_trips_by_route_id = trips_df.to_dict(orient='index')

    o_d_distances = pandas.DataFrame()
    for route_id in longest_trips_by_route_id.keys():
        trip_id = longest_trips_by_route_id[route_id]['trip_id']

        trip_stop_times_df = stop_times_df.loc[
            stop_times_df.trip_id == trip_id,
            ['route_id','stop_sequence','stop_id','shape_dist_traveled']].copy()
        trip_stop_times_df.sort_values(by='stop_sequence', inplace=True)
        trip_stop_times_df.reset_index(drop=True, inplace=True)
        # sometimes the stop sequence skips one so re-number
        trip_stop_times_df['stop_sequence'] = trip_stop_times_df.index
        # print(trip_stop_times_df)

        # convert to links
        link_df = trip_stop_times_df.rename({'stop_id':'stop_id_A'})
        link_df['stop_sequence_B'] = link_df['stop_sequence'] + 1
        # print(link_df)
        # join to self to get links
        link_df = pandas.merge(
            left = link_df,
            right = link_df,
            left_on = ['route_id','stop_sequence_B'],
            right_on = ['route_id','stop_sequence'],
            how = 'left',
            suffixes=['_A','_B']
        )
        # drop the last row, keep only relevant columns
        link_df = link_df.loc[pandas.notnull(link_df.stop_id_B),
                              ['route_id',
                              'stop_id_A','stop_id_B',
                              'shape_dist_traveled_A','shape_dist_traveled_B',
                              'stop_sequence_A','stop_sequence_B']]
        link_df['stop_sequence_B'] = link_df['stop_sequence_B'].astype(int)
        link_df['dist'] = link_df['shape_dist_traveled_B'] - link_df['shape_dist_traveled_A']
        link_df.drop(columns=['shape_dist_traveled_A','shape_dist_traveled_B'], inplace=True)
        # drop stop_id_A==stop_id_B links
        link_df = link_df.loc[ link_df.stop_id_A != link_df.stop_id_B ].reset_index(drop=True)
        # print("link_df for route {}:\n{}".format(route_id, link_df))

        # now we have a link-based dataframe with columns
        # route_id, stop_id_A, stop_id_B, stop_sequence_A, stop_sequence_B, dist
        # fill out all ODs on this line
        trip_dicts = []
        for stop_sequence_A in link_df['stop_sequence_A'].to_list():
            for stop_sequence_B in link_df['stop_sequence_B'].to_list():
                if stop_sequence_A >= stop_sequence_B: continue
                # print("stop_sequence A_B: {}_{}".format(stop_sequence_A, stop_sequence_B))
                trip_dict = { 'route_id':route_id}
                trip_df = link_df.loc[(link_df.stop_sequence_A >= stop_sequence_A) &
                                      (link_df.stop_sequence_B <= stop_sequence_B)]
                trip_dict['stop_sequence_A'] = stop_sequence_A
                trip_dict['stop_sequence_B'] = stop_sequence_B
                trip_dict['stop_id_A'] = trip_df.iloc[0]['stop_id_A']
                trip_dict['stop_id_B'] = trip_df.iloc[-1]['stop_id_B']
                trip_dict['dist'] = trip_df['dist'].sum()
                trip_dicts.append(trip_dict)
        trip_ods_df = pandas.DataFrame(data=trip_dicts)
        # print(trip_ods_df)

        # having stop_sequence_A, stop_sequence_B there was handy for looking at this table
        # but we don't really need it going forward
        trip_ods_df.drop(columns=['stop_sequence_A','stop_sequence_B'], inplace=True)

        o_d_distances = pandas.concat([o_d_distances, trip_ods_df])

    # print("o_d_distances.head(30):\n{}".format(o_d_distances.head(30)))
    # groupby stop_id_A, stop_id_B -- since the lines have shared segments
    o_d_distances = o_d_distances.groupby(by=['stop_id_A','stop_id_B']).agg(
        dist      = pandas.NamedAgg(column='dist', aggfunc='mean'),
        route_ids = pandas.NamedAgg(column='route_id', aggfunc=lambda text: ','.join(text))
    ).reset_index()
    print("o_d_distances length={:,} head():\n{}".format(len(o_d_distances), o_d_distances.head()))
    print("o_d_distances.route_ids.value_counts():\n{}".format(
        o_d_distances.route_ids.value_counts()
    ))
    
    all_transfer_trips_df = pandas.DataFrame()
    # create transfer trips by transferring at these stations
    for TRANSFER in ['DALY','MCAR','BAYF']:
        transfer_trips_df = create_transfer_ods(o_d_distances, TRANSFER)
            
        all_transfer_trips_df = pandas.concat([all_transfer_trips_df, transfer_trips_df])
    print("all_transfer_trips_df length: {:,}".format(len(all_transfer_trips_df)))

    # put transfers together with direct links
    o_d_distances = pandas.concat([o_d_distances, all_transfer_trips_df])

    # do COLS transfer in second pass
    transfer_trips_df = create_transfer_ods(o_d_distances, TRANSFER='COLS')
    print("transfer_trips_df for COLS length: {:,}".format(len(transfer_trips_df)))
    o_d_distances = pandas.concat([o_d_distances, transfer_trips_df])

    # check if we have duplicates
    o_d_distances_grouped = o_d_distances.groupby(by=['stop_id_A','stop_id_B'])
    for group_name, df_group in o_d_distances_grouped:
        if len(df_group) > 1:
            print("{} len={}:\n{}".format(group_name, len(df_group), df_group))

    # add zero distance for all station-to-same-station
    stop_ids = o_d_distances['stop_id_A'].drop_duplicates()
    print("Have {} unique stop_ids".format(len(stop_ids)))
    same_station_OD_df = pandas.DataFrame(stop_ids)
    same_station_OD_df['stop_id_B'] = same_station_OD_df['stop_id_A']
    same_station_OD_df['dist'] = 0.0
    same_station_OD_df['route_ids'] = 'N/A'
    # print(same_station_OD_df.head())
    o_d_distances = pandas.concat([o_d_distances, same_station_OD_df])

    o_d_distances.to_csv(OUTPUT_BART_OD_DISTS, index=False)
    print("Wrote {:,} rows to {}".format(len(o_d_distances), OUTPUT_BART_OD_DISTS))
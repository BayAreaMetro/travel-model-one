REM Run this for a set of networks
REM e.g. M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_v35

@echo on
Setlocal EnableDelayedExpansion

for %%y in (2015 2023 2035 2050) do (

    rem only do Baseline for past years
    if %%y LEQ 2023 (
        set NETWORKS=Baseline
    ) else (
        set NETWORKS=Baseline Blueprint BPwithoutTransit
    )
    echo Processing %%y and networks !NETWORKS!

    for %%X in (!NETWORKS!) do (

        set shapedir=net_%%y_%%X\shapefiles
        if exist !shapedir! (
            echo !shapedir! exists
        ) else (
            echo !shapedir! does not exist
            mkdir !shapedir!
        )
        if exist !shapedir!\network_trn_links.shp (
            echo !shapedir!\network_trn_links.shp exists
        ) else (
            rem export
            cd !shapedir!
            python X:\travel-model-one-master\utilities\cube-to-shapefile\cube_to_shapefile.py --linefile ..\trn\transitLines.lin ..\hwy\freeflow.net
            cd ..
            cd ..
        )
    )
)

:done
import orca


@orca.table(cache=True)
def land_use(store):
    return store["land_use/taz_data"]

import orca

@orca.table(cache=True)
def land_use(store):
    return store["land_use/taz_data"]

@orca.column("land_use")
def terminal_time(land_use):
	return land_use.TERMINAL

@orca.column("land_use")
def hourly_parking_cost_for_workers(land_use):
	return land_use.PRKCST 

@orca.column("land_use")
def topology(land_use):
	return land_use.TOPOLOGY 

@orca.column("land_use")
def total_households(land_use):
    return land_use.local.TOTHH

@orca.column("land_use")
def total_employment(land_use):
    return land_use.local.TOTEMP

@orca.column("land_use")
def total_acres(land_use):
    return land_use.local.TOTACRE

@orca.column("land_use")
def household_density(land_use):
    return land_use.total_households / land_use.total_acres

@orca.column("land_use")
def employment_density(land_use):
    return land_use.total_employment / land_use.total_acres

@orca.column("land_use")
def density_index(land_use):
    return (land_use.household_density * land_use.employment_density) / \
        (land_use.household_density + land_use.employment_density)
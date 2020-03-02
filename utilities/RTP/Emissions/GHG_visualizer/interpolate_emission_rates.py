
import os
import pandas as pd

InputEmissionRates_df = pd.read_excel(os.path.join(os.getcwd(), "yr2035_passveh_CO2_rates.xlsx"), header=1, index_col=1,skiprows=2,nrows=10)
# The emission rates are stored in InputEmissionRates_df.loc[county,speed]

# max speed in miles per hour
max_speed = 100


# ---------------------------------------------------------------------------

# the eq. should look like (r(alameda, high_mph) - r(alameda, low_mph)) / 5 * (mph - low_mph) + r(alameda, low_mph)

# note that there is a space after the county name
counties = ["Alameda ", "Contra Costa ", "Marin ", "Napa ", "San Francisco ", "San Mateo ", "Santa Clara ", "Solano ", "Sonoma "]
# ref_speed = ["5 mph", "10 mph", "15 mph", "20 mph", "25 mph", "30 mph", "35 mph", "40 mph", "45 mph", "50 mph", "55 mph", "60 mph", "65 mph", "70 mph"]

# for c in counties:
#    for s in ref_speed:
#            d = InputEmissionRates_df.loc[c,s]
#            print(d)


# create a new data frame
Interpolated_df = pd.DataFrame(columns = counties)

for c in counties:
    for mph in range(1, max_speed):

        quotient = (mph // 5)*5 # In Python, you can calculate the quotient with //
        ref_bottom = str(quotient) + " mph"

        quotient_plus5 = quotient + 5
        ref_top = str(quotient_plus5) + " mph"

        if mph >=5 and mph<70:
            Interpolated_df.loc[mph, c] = (InputEmissionRates_df.loc[c,ref_top] - InputEmissionRates_df.loc[c,ref_bottom]) / 5 * (mph - quotient) + InputEmissionRates_df.loc[c,ref_bottom]

        if mph <5: # use 10 mph and 5 mph to extrapolate
            ref_top = "10 mph"
            ref_bottom = "5 mph"
            Interpolated_df.loc[mph, c] = ((InputEmissionRates_df.loc[c,ref_top] - InputEmissionRates_df.loc[c,ref_bottom]) / 5  ) * -1 * (5 - mph) + InputEmissionRates_df.loc[c,ref_bottom]

        if mph >=70: # use 65 mph and 70 mph to extrapolate
            ref_top = "70 mph"
            ref_bottom = "65 mph"
            Interpolated_df.loc[mph, c] = ((InputEmissionRates_df.loc[c,ref_top] - InputEmissionRates_df.loc[c,ref_bottom]) / 5) * (mph - 70) + InputEmissionRates_df.loc[c,ref_top]

# add a mph column
Interpolated_df['mph'] = Interpolated_df.reset_index().index + 1

# drop the space after the county name
Interpolated_df = Interpolated_df.rename(columns={"Alameda ": "Alameda", "Contra Costa ": "Contra Costa", "Marin ": "Marin", "Napa ": "Napa", "San Francisco ": "San Francisco","San Mateo ": "San Mateo", "Santa Clara ": "Santa Clara", "Solano ": "Solano", "Sonoma ": "Sonoma"})

# reorder the columns
Interpolated_df = Interpolated_df[["mph", "Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"]]

output_filename = os.path.join(os.getcwd(), "interpolated.csv")
Interpolated_df.to_csv(output_filename, header=True, index=False)

package com.pb.models.censusdata;

import com.pb.common.datafile.TextFile;

import java.util.*;

/**
 * The {@code PersonAge} class is used to define the marginals for person age controls in population generation.
 *
 * @author crf
 *         Started: Oct 9, 2010 8:20:58 AM
 */
public class PersonAge {
    private final Map<String,Integer> ageRanges; //age range to upper limit of age (this will be linked so that its iteration order is well-defined
    private final Map<Integer,Map<String,Double>> ageRangeProportions; //map from year to map of age range to proportion in population  - sorted by year
    private boolean enabled;

    /**
     * Constructor specifying NED definition file and year that it applies to.  Format of NED definition file is:
     * <p>
     * <pre>
     *     age_minimum,population,share
     * </pre>
     * <p>
     * where age_minimum is the minimum age for the category, population is the absolute population count, and share is
     * the share of the category for the overall population.
     *
     * @param definitionFile
     *        The NED definition file.
     *
     * @param year
     *        The (calendar) year this instance applies to.
     */
    //kind of hacky to have completely different definition files distinguished by "year" parameter, but it will do for now
    //  maybe later can refactor into factory calls
    public PersonAge(String definitionFile, Integer year) {
        enabled = definitionFile != null;
        if (enabled) {
            ageRanges = new LinkedHashMap<String,Integer>();
            ageRangeProportions = new TreeMap<Integer,Map<String,Double>>();
            if (year != null)
                readPersonAgeSpecificationFromNed(definitionFile,year);
            else
                readPersonAgeSpecification(definitionFile);
        } else {
            ageRanges = null;
            ageRangeProportions = null;
        }
    }

    /**
     * Constructor specifying person age definition file. This file is formatted as:
     * <p>
     * <pre>
     *     AgeRange,UpperAgeLimit,1990persons,2000persons, etc.
     * </pre>
     * <p>
     * where AgeRange is the name of the category, UpperAgeLimit is the highest age that belongs in that category, and
     * XXXXpersons is the relative number of persons for that category in the year XXXX.  Note that the person age categories
     * need to be sorted in order (low to high) of UpperAgeLimit.
     *
     * @param definitionFile
     *        The definition file path.
     */
    public PersonAge(String definitionFile) {
        this(definitionFile,null);
    }

    private void readPersonAgeSpecificationFromNed(String definitionFile, Integer year) {
        //format of NED file is:
        // age_minimum,population,share
        // it is for one year, but that will be fine (and consistent) in this context

        TextFile tf = new TextFile(definitionFile);
        Iterator<String> lineIterator = tf.iterator();

        lineIterator.next(); //skip first line

        Map<Integer,Double> tempAgeMinToProportion = new TreeMap<Integer,Double>();
        //age categories might be out of order
        while (lineIterator.hasNext()) {
            String ln = lineIterator.next().trim();
            if (ln.length() == 0)
                continue;
            String[] line = ln.split(",");
            tempAgeMinToProportion.put(Integer.parseInt(line[0].trim()),Double.parseDouble(line[2]));
        }

        //fill in ageRanges in correct order
        ageRangeProportions.put(year,new LinkedHashMap<String,Double>());
        boolean first = true;
        int min = -1; //won't be used at this value
        double lastProp = -1;
        for (int a : tempAgeMinToProportion.keySet()) {
            if (first) {
                first = false;
            } else {
                String range = min + "-" + (a-1);
                ageRanges.put(range,a-1);
                ageRangeProportions.get(year).put(range,lastProp);
            }
            min = a;
            lastProp = tempAgeMinToProportion.get(a);
        }
        String range = min + "+";
        ageRanges.put(range,100);
        ageRangeProportions.get(year).put(range,lastProp);
    }

    private void readPersonAgeSpecification(String definitionFile) {
        //file should be: AgeRange,UpperAgeLimit,1990households,2000households, etc.
        //e.g.: 0-3,3,4,.2
        //      4-10,10,10,.3  etc.

        //don't muck with table data set - just parse the text file
        //the issue is that we have string then int/double data, but an unknown number of columns
        // to get table data set to work correctly, would have to read the header by hand first to
        // find # of columns; easier to just read the whole file

        TextFile tf = new TextFile(definitionFile);
        Iterator<String> lineIterator = tf.iterator();

        String[] header = lineIterator.next().split(",");
        int[] yearIndex = new int[header.length]; //ignores first two columns
        for (int i = 2; i < header.length; i++) {
            int year;
            try {
                year = Integer.parseInt(header[i].toLowerCase().trim().replace("persons",""));
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("Invalid age range proportion header, should be [year]persons: " + header[i]);
            }
            yearIndex[i] = year;
            ageRangeProportions.put(year,new LinkedHashMap<String,Double>()); //need to maintain ordering
        }

        //now read rest of file
        while (lineIterator.hasNext()) {
            String ln = lineIterator.next().trim();
            if (ln.length() == 0)
                continue;
            String[] line = ln.split(",");
            String ageRange = line[0].trim();
            ageRanges.put(ageRange,Integer.parseInt(line[1].trim()));

            for (int i = 2; i < line.length; i++) {
                double value;
                try {
                    value = Double.parseDouble(line[i]);
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException(String.format("Invalid age range proportion for %s in year %d: %s",ageRange,yearIndex[i],line[i]));
                }
                if (value < 0)
                    throw new IllegalArgumentException(String.format("Invalid age range proportion (< 0.0) for %s in year %d: %s",ageRange,yearIndex[i],line[i]));
                ageRangeProportions.get(yearIndex[i]).put(ageRange,value);
            }
        }

        //loop through and proportionalize everything
        for (int year : ageRangeProportions.keySet()) {
            double total = 0.0;
            Map<String,Double> props = ageRangeProportions.get(year);
            for (String ageRange : props.keySet())
                total += props.get(ageRange);
            for (String ageRange : props.keySet())
                props.put(ageRange,props.get(ageRange)/total);
        }
    }

    /**
     * Set whether this controller is enabled or not.  If it is not enabled, then none of the functions (outside of those
     * dealing with enabling/disabling) will work.
     *
     * @param enabled
     *        If {@code true}, then this controller will be enabled, if {@code false}, it will not be.
     */
    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    /**
     * Determine whether this controller is enabled or not.
     *
     * @return {@code true} if this controller is enabled, {@code false} if not.
     */
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Get the age range category names for this controller, in order.
     *
     * @return this controller's age range category names.
     *
     * @throws IllegalStateException if this controller is not enabled.
     */
    public String[] getAgeRanges() {
        if (!enabled)
            throw new IllegalStateException("PersonAge not enabled");
        return ageRanges.keySet().toArray(new String[ageRanges.size()]);
    }

    /**
     * Get the category index for the specified age. That is, the age passed into this method will belong to the category
     * {@code getAgeRanges()[i]}, where {@code i} is the value returned by this method.  No checks are made as to the
     * validity of {@code age} (such as whether it is less than 0 or larger than some upper bound).
     *
     * @param age
     *        The age in question.
     *
     * @return the category index for {@code age}.
     *
     * @throws IllegalStateException if this controller is not enabled.
     */
    public int getAgeCategoryIndex(int age) {
        if (!enabled)
            throw new IllegalStateException("PersonAge not enabled");
        int counter = -1;
        for (String ageRange : ageRanges.keySet()) {
            counter++;
            if (age < ageRanges.get(ageRange))
                break;
        }
        return counter;
    }

    /**
     * Get the marginal person age targets for a given year and a total population. The returned marginals will sum to
     * the total persons value passed to this method. This controller will pick the closest year to {@code year} from
     * the available control years read in from the definition file at construction time.  In case of ties, the higher
     * control year is selected.
     *
     * @param year
     *        The target year for the marginals.
     *
     * @param totalPersons
     *        The total population.
     *
     * @return the marginals for {@code year} corresponding to {@code totalPersons}.
     *
     * @throws IllegalStateException if this controller is not enabled.
     */
    public int[] getMarginalAgeRangeTargets(int year, int totalPersons) {
        if (!enabled)
            throw new IllegalStateException("PersonAge not enabled");
        //pick the year closest to passed-in year
        int targetYear = -1;
        int lastYear = -99999;
        for (int yearKey : ageRangeProportions.keySet()) {
            if (year < yearKey) {
                targetYear = (year - lastYear) > (yearKey - year) ? yearKey : lastYear;
                break;
            } else {
                lastYear = yearKey;
            }
        }
        if (targetYear < 0)
            targetYear = lastYear;

        //now spread persons amongst ranges
        Map<String,Double> props = ageRangeProportions.get(targetYear);
        int[] targets = new int[ageRanges.size()];
        double[] remainders = new double[ageRanges.size()];
        int remainingPersons = totalPersons;
        int counter = 0;
        for (String ageRange : props.keySet()) {
            double hh = props.get(ageRange)*totalPersons;
            targets[counter] = (int) Math.round(hh);
            remainders[counter] = hh - targets[counter];
            remainingPersons -= targets[counter];
            counter++;
        }


        String message2 = props.toString();
        String message3 = Arrays.toString(remainders);
        String message4 = "" + remainingPersons;
        String message5 = Arrays.toString(targets);

        //shift marginals to exactly equal person total
        while (remainingPersons != 0) {
            boolean negativeRemaining = remainingPersons < 0;
            int shift = negativeRemaining ? -1 : 1;
            double gap = 0;
            int index = -1;
            for (int i = 0; i < remainders.length; i++)
                if ((negativeRemaining ? remainders[i] < 0 : remainders[i] > 0)  && remainders[i]*shift > gap)
                    index = i;
            if (index < 0) {
                throw new IllegalStateException(String.format("Issue with remainders, persons remaining (%d) cannot be dealt with by remainders %s",remainingPersons,Arrays.toString(remainders)) +
                "\n" + message2 +
                "\n" + message3 +
                "\n" + message4 +
                "\n" + message5);
            }
            targets[index] -= shift;
            remainders[index] = 0;
            remainingPersons -= shift;
        }

        return targets;
    }
}

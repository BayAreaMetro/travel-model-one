/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.models.synpop.daf;

/**
 * MESSAGE_IDS is a class that ...
 *
 * @author Christi Willison
 * @version 1.0,  May 14, 2009
 */
public class MESSAGE_IDS {


    /* ****** MESSAGE CONENT ****** */
    public static final String CATEGORY = "HH Category";
    public static String CATEGORY_LABEL = "HH Category Label";
    public static final String RP_ASSIGNER_RESULTS = "assigner results";

    public static String REGION_DOLLARS = "Region Dollars By Job";

    public static final String RP_CATEGORY_COUNT = "category count";
    public static final String RP_ARRAY_SIZE = "hh array size";
    public static final String RP_SUMMARY_HHS = "totalHhsByTaz";
    public static final String RP_SUMMARY_HH_INCOME = "totalHhIncomeByTaz";
    public static final String RP_SUMMARY_PERSONS = "totalPersonsByTaz";
    public static final String RP_SUMMARY_WORKERS = "totalWorkersByTaz";
    public static final String RP_SUMMARY_HHS_BY_CATEGORY = "totalHhsByTazCategory";
    public static final String RP_SUMMARY_PERSON_AGES = "personAgesByTaz";


    /* ****** MESSAGE IDS ****** */
    public static final String HA_WORK_MESSAGE_ID = "assigner work message";
    public static final String HA_SEND_SUMMARIES_ID = "hh assigner send summaries";

    public static final String RP_ASSIGNER_HH_ARRAY_SIZE_ID = "assigner hh array size message";
    public static final String RP_ASSIGNER_RESULTS_MESSAGE_ID = "assigner results message";
    public static final String RP_WRITE_SPG2_OUTPUT_FILE_MESSAGE_ID = "write summary results message";
    public static final String RP_ASSIGNER_SUMMARY_RESULTS_ID = "assigner summary results message";
    public static final String RP_WRITE_ZONAL_SUMMARY_ID = "write summary results message";

}

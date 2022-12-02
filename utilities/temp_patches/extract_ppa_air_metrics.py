#
# script to crawl a set of model dirs and pull their air metrics
#

import os, re, sys
import pandas

MODEL_DIRS_PATH_DEFAULT = "L:\\RTP2021_PPA\\Projects"
BASE_RUN_ID_RE = re.compile(r"2050_TM151_PPA_(BF|CG|RT)_(11|12)$")
PROJECT_RUN_ID_RE = re.compile(r"(2050_TM151_PPA_(BF|CG|RT)_(11|12))_(.*)$")


def read_air_metrics(model_id, base_id, directory, air_metrics_df):
    """
    Reads the metrics from the given directory's output and appends to metrics_df
    """
    metrics_file = os.path.join(directory, "OUTPUT", "metrics", "auto_times.csv")
    if not os.path.exists(metrics_file):
        # print("Not found: {}".format(metrics_file))
        return air_metrics_df

    metrics_df = pandas.read_csv(metrics_file)
    metrics_df = metrics_df.loc[metrics_df.Mode.str.endswith("_air")]
    metrics_df["model_id"] = model_id
    if model_id != base_id:
        metrics_df["base_id"] = base_id

    # drop income -- it's not set for air
    metrics_df.drop(columns=["Income"], inplace=True)

    air_metrics_df = pandas.concat([air_metrics_df, metrics_df])
    return air_metrics_df


if __name__ == "__main__":

    dirs = sorted(os.listdir(MODEL_DIRS_PATH_DEFAULT))

    base_metrics_df = pandas.DataFrame()
    project_metrics_df = pandas.DataFrame()

    for directory in dirs:

        m = BASE_RUN_ID_RE.match(directory)
        if m != None:
            print("Baseline run found: {}".format(directory))

            base_metrics_df = read_air_metrics(
                model_id=directory,
                base_id=directory,
                directory=os.path.join(MODEL_DIRS_PATH_DEFAULT, directory),
                air_metrics_df=base_metrics_df,
            )

        elif os.path.isdir(os.path.join(MODEL_DIRS_PATH_DEFAULT, directory)):

            # else if it's a project and subdirectories start with that
            subdirs = sorted(
                os.listdir(os.path.join(MODEL_DIRS_PATH_DEFAULT, directory))
            )

            for subdirectory in subdirs:

                m2 = PROJECT_RUN_ID_RE.match(subdirectory)
                if m2 != None:

                    print(
                        "Project run found: {}  base_dir: {}".format(
                            subdirectory, m2.group(1)
                        )
                    )

                    project_metrics_df = read_air_metrics(
                        model_id=subdirectory,
                        base_id=m2.group(1),
                        directory=os.path.join(
                            MODEL_DIRS_PATH_DEFAULT, directory, subdirectory
                        ),
                        air_metrics_df=project_metrics_df,
                    )
    # print(project_metrics_df)
    # print(base_metrics_df)

    # join project metrics with base
    metrics_df = pandas.merge(
        left=project_metrics_df,
        right=base_metrics_df,
        left_on=["base_id", "Mode"],
        right_on=["model_id", "Mode"],
        how="left",
        suffixes=("", " base"),
    )
    print(metrics_df.head())
    # output
    OUTFILE = "air_metrics_baselines_11_12.csv"
    metrics_df.to_csv(OUTFILE, index=False)
    print("Wrote air metrics to {}".format(OUTFILE))

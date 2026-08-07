import logging
import sys
import yaml
import time
import functools
from typing import Callable, Optional
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED


import geopandas as gpd





def setup_logging(
    level: int = logging.INFO,
    log_dir: str | None = None,
    log_name: str = "pipeline",
) -> Path | None:
    """
    Configure root logger with a consistent format for all pipeline scripts.

    If log_dir is provided, logs are written to both stdout and a timestamped
    log file. Otherwise, logs are written only to stdout.
    """
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout)
    ]

    log_path = None

    if log_dir is not None:
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = Path(log_dir) / f"{log_name}_{timestamp}.log"

        handlers.append(
            logging.FileHandler(log_path, mode="w", encoding="utf-8")
        )

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )

    return log_path


def load_config(config_path: str = "configs/config.yaml") -> dict:
    """Load YAML config from *config_path*."""
    with open(config_path) as f:
        return yaml.safe_load(f)



def timeit(func: Callable) -> Callable:
    """Decorator to time a function and log duration and return-type diagnostics.

    The decorator logs start/finish messages including elapsed seconds. If the
    wrapped function returns a pandas DataFrame the decorator will log its
    shape using `log_df`.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.info("Starting %s", func.__name__)
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.info("Finished %s in %.3f s", func.__name__, elapsed)

        # Log DataFrame diagnostics for common pipeline return types
        try:
            log_df(logger, result, label=f"{func.__name__}.result")
        except Exception:
            logger.debug("Could not log result diagnostics for %s", func.__name__, exc_info=True)

        return result

    return wrapper


def save_shapefile(
    gdf: gpd.GeoDataFrame,
    path: Path,
    crs: Optional[str] = None,
) -> None:
    """
    Save a GeoDataFrame as a shapefile and ZIP archive inside a
    self-contained folder.

    If ``crs`` is provided:
        - Reproject the GeoDataFrame if it already has a CRS.
        - Assign the CRS if it does not have one.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Input geospatial data.

    path : pathlib.Path
        Requested output path. The filename stem is used for both the
        output folder and shapefile name.

    crs : str, optional
        Target CRS, such as ``"EPSG:4326"``.
    """
    path = Path(path).resolve()

    # Use the requested filename as the folder and shapefile name.
    output_name = path.stem
    output_folder = path.parent / output_name
    shapefile_path = output_folder / f"{output_name}.shp"
    zip_path = path.with_suffix(".zip")

    output_folder.mkdir(parents=True, exist_ok=True)

    # Avoid modifying the original GeoDataFrame.
    output_gdf = gdf.copy()

    if crs is not None:
        if output_gdf.crs is None:
            output_gdf = output_gdf.set_crs(crs)
        else:
            output_gdf = output_gdf.to_crs(crs)


    # Write the individual shapefile components.
    output_gdf.to_file(
        shapefile_path,
        driver="ESRI Shapefile",
        engine="pyogrio",
        index=False,
    )

    # Find all components created by GeoPandas/Pyogrio.
    components = [
        component
        for component in output_folder.glob(f"{output_name}.*")
        if component.is_file()
        and component.suffix.lower() != ".zip"
    ]

    if not components:
        raise RuntimeError(
            f"No shapefile components were created for {shapefile_path}"
        )

    # Create the ZIP inside the same self-contained folder.
    with ZipFile(
        zip_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        for component in components:
            archive.write(
                component,
                arcname=component.name,
            )

def save(data, filepath: str, overwrite: bool = True, crs: Optional[str] = None) -> None:
    """
    Save a dataframe or geodataframe based on file extension.

    Supports:
        - CSV (.csv)
        - Parquet (.parquet)
        - Shapefile (.shp)

    Ensures output directory exists.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        data.to_csv(path, index=False)

    elif suffix == ".parquet":
        data.to_parquet(path, index=False)

    elif suffix == ".shp":
        if not isinstance(data, gpd.GeoDataFrame):
            raise ValueError("Shapefile output requires a GeoDataFrame")
        save_shapefile(data, path, crs)

    else:
        raise ValueError(f"Unsupported format: {suffix}")

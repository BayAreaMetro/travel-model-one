import logging
import sys
import yaml
import time
import functools
from typing import Callable, Optional
from datetime import datetime
from pathlib import Path


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
    path: str,
    crs: Optional[str] = None,
) -> None:
    """
    Save a GeoDataFrame as a shapefile.

    If `crs` is provided:
        - If gdf has a CRS → reproject to the provided CRS
        - If gdf has no CRS → assign the provided CRS

    Parameters
    ----------
    gdf : GeoDataFrame
        Input geospatial data.
    path : str
        Output shapefile path.
    crs : Optional[str]
        Target CRS (e.g., 'EPSG:4326').
    """
    if crs is not None:
        if gdf.crs is None:
            gdf = gdf.set_crs(crs)
        else:
            gdf = gdf.to_crs(crs)

    gdf.to_file(path)

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

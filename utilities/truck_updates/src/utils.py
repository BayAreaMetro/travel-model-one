"""Shared utilities for the CSF-to-MTC pipeline."""

import logging
import os
import sys
import yaml
import time
import functools
from typing import Any, Callable, Optional

import pandas as pd
import geopandas as gpd

def save_shapefile(
    gdf: gpd.GeoDataFrame,
    path: str,
    crs: Optional[str] = None,
) -> None:
    """
    Save a shapefile to disk.
    """
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    if crs is not None:
        if gdf.crs is None:
            gdf = gdf.set_crs(crs)
        else:
            gdf = gdf.to_crs(crs)
    gdf.to_file(path)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format for all pipeline scripts."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


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

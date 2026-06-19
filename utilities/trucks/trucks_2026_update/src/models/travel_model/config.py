"""Config models for the scenario runner.

One YAML file describes everything and is validated with these Pydantic models
before any scenario runs, so a typo fails immediately. Load it with::

    RunConfig.model_validate(yaml.safe_load(open(path)))
"""
from __future__ import annotations

from pydantic import BaseModel


class Replacement(BaseModel):
    """A single file swap applied to an extracted scenario.

    Parameters
    ----------
    source : str
        A local file path or a GitHub URL (auto-detected at run time by
        :func:`~models.travel_model.pipeline.resolve_source`).
    destination : str
        Path relative to the scenario root; must already exist (the tool never
        creates new files).
    """

    source: str
    destination: str


class Scenario(BaseModel):
    """One model scenario: a base extract with a few files replaced.

    Parameters
    ----------
    name : str
        Scenario name; also the folder created under ``output_root``.
    replacements : list[Replacement]
        Files to swap in after extraction. Empty means "untouched base".
    skip_if_exists : bool
        If ``True`` and the scenario folder already exists, skip the rebuild and
        the ``.bat`` run; conversion still runs. Defaults to ``False``.
    base_zip : str | None
        Optional per-scenario override of the shared ``RunConfig.base_zip``.
    """

    name: str
    replacements: list[Replacement] = []
    skip_if_exists: bool = False
    base_zip: str | None = None


class RunConfig(BaseModel):
    """The whole YAML file: a shared base zip, an output root, and scenarios.

    Parameters
    ----------
    base_zip : str
        Shared full-model zip, used unless a scenario overrides it.
    output_root : str
        Parent folder under which each scenario's folder is created.
    scenarios : list[Scenario]
        Scenarios to run, in order.
    """

    base_zip: str
    output_root: str
    iteration: str
    scenarios: list[Scenario]


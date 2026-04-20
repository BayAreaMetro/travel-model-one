"""Fetches the MTC examples from the URLs specified in the manifest and saves them.

Pretty clunky, as it creates nested files, but whatever its a one time thing.
"""

from importlib.resources import files
from pathlib import Path

import yaml
from activitysim.examples import external

# Load manifest
_MANIFEST = yaml.safe_load(
    files("activitysim.examples").joinpath("external_example_manifest.yaml").read_text()
)
_OUTPUT_DIR = Path.cwd() / "base-model"
_OUTPUT_DIR.mkdir(exist_ok=True)


EXAMPLES = [
    "prototype_mtc",
    # "prototype_mtc_extended",
    # "legacy_mtc" # Doesn't exist anymore?
]

for example in EXAMPLES:
    example_info = _MANIFEST[example]
    external.download_external_example(
        name=example,
        working_dir=_OUTPUT_DIR / example,
        url=example_info["url"],
        assets=example_info.get("assets", {}),
    )


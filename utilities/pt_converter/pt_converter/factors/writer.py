"""Write PT FACTORI files for the TM1 assignment user classes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile

from ..errors import OutputWriteError, ValidationError
from .models import FactorClass, FactorSource, ModeFactor


PATH_FACTORS = {
    "loc": ((80, 139),),
    "exp": ((120, 139),),
    "lrf": ((80, 99), (120, 139)),
    "hvy": ((130, 139),),
    "com": (),
}

RUN_FACTORS = {
    "loc": ("2.0", "1.0", "1.5", "1.5", "1.5", "1.5", "1.5"),
    "exp": ("2.0", "1.5", "1.0", "1.5", "1.5", "1.5", "1.5"),
    "lrf": ("2.0", "1.5", "1.5", "1.0", "1.0", "1.5", "1.5"),
    "hvy": ("2.0", "1.5", "1.2", "1.1", "1.1", "1.0", "1.5"),
    "com": ("2.0", "1.5", "1.2", "1.1", "1.1", "1.1", "1.0"),
}

MODE_RANGES = ((1, 9), (10, 79), (80, 99), (100, 109), (110, 119), (120, 129), (130, 139))


@dataclass(frozen=True, slots=True)
class FactorWriteResult:
    """Paths and counts produced by factor-file preparation."""

    factor_paths: tuple[Path, ...]
    report_path: Path

    @property
    def factor_count(self) -> int:
        return len(self.factor_paths)


def tm1_factor_source() -> FactorSource:
    """Return the 15 user classes defined by TM1 TransitAssign.job."""

    classes: list[FactorClass] = []
    number = 1
    for access, egress in (("wlk", "wlk"), ("drv", "wlk"), ("wlk", "drv")):
        for path in ("loc", "exp", "lrf", "hvy", "com"):
            factors = tuple(
                ModeFactor(first, last, Decimal(value))
                for (first, last), value in zip(MODE_RANGES, RUN_FACTORS[path], strict=True)
            )
            classes.append(
                FactorClass(
                    number=number,
                    access=access,
                    path=path,
                    egress=egress,
                    run_factors=factors,
                    deleted_modes=PATH_FACTORS[path],
                    deleted_access_modes=(2, 6, 7) if access == "wlk" else (1, 6, 7),
                    deleted_egress_modes=(1, 2, 7) if egress == "wlk" else (1, 2, 6),
                )
            )
            number += 1
    return FactorSource(tuple(classes), wait_factor=Decimal("2.8"), wait_curve=1)


class FactorWriter:
    """Serialize PT factors without embedding time-period or iteration logic."""

    def write(
        self,
        source: FactorSource,
        output_directory: Path,
        maximum_stop_node: int,
    ) -> FactorWriteResult:
        self._validate(source, maximum_stop_node)
        output_directory.mkdir(parents=True, exist_ok=True)
        factor_paths: list[Path] = []
        for factor_class in source.classes:
            path = output_directory / f"{factor_class.name}.fac"
            self._write_text(path, self._render(source, factor_class, maximum_stop_node))
            factor_paths.append(path)

        report_path = output_directory / "factor_conversion_report.json"
        self._write_text(
            report_path,
            json.dumps(self._report(source, factor_paths, maximum_stop_node), indent=2) + "\n",
        )
        return FactorWriteResult(tuple(factor_paths), report_path)

    @staticmethod
    def _validate(source: FactorSource, maximum_stop_node: int) -> None:
        if maximum_stop_node < 1:
            raise ValidationError("Cannot write PT factors without a positive transit stop node.")
        numbers = [item.number for item in source.classes]
        names = [item.name for item in source.classes]
        if numbers != list(range(1, len(source.classes) + 1)):
            raise ValidationError("PT factor user-class numbers must be consecutive and start at 1.")
        if len(names) != len(set(names)):
            raise ValidationError("PT factor user-class names must be unique.")
        if len(source.classes) != 15:
            raise ValidationError(f"TM1 requires 15 PT factor classes; found {len(source.classes)}.")

    @staticmethod
    def _render(source: FactorSource, item: FactorClass, maximum_stop_node: int) -> str:
        node_range = f"1-{maximum_stop_node}"
        rendered = [
            ";;<<PT>><<FACTORS>>;;",
            f"; User class {item.number}: {item.access}/{item.path}/{item.egress}",
            f"RUNFACTOR={_run_factors(item.run_factors)}",
        ]
        if item.deleted_modes:
            rendered.append(f"DELMODE={_ranges(item.deleted_modes)}")
        rendered.extend(
            (
                f"DELACCESSMODE={_values(item.deleted_access_modes)}",
                f"DELEGRESSMODE={_values(item.deleted_egress_modes)}",
                f"IWAITCURVE={source.wait_curve}, NODES={node_range}",
                f"XWAITCURVE={source.wait_curve}, NODES={node_range}",
                f"WAITFACTOR={_decimal(source.wait_factor)}, NODES={node_range}",
                "SERVICEMODEL=FREQUENCY",
            )
        )
        return "\n".join(rendered) + "\n"

    @staticmethod
    def _report(
        source: FactorSource,
        paths: list[Path],
        maximum_stop_node: int,
    ) -> dict[str, object]:
        return {
            "factor_file_count": len(paths),
            "time_period_specific": False,
            "iteration_specific": False,
            "maximum_stop_node": maximum_stop_node,
            "user_classes": [
                {
                    "number": item.number,
                    "name": item.name,
                    "file": path.name,
                    "access": item.access,
                    "path": item.path,
                    "egress": item.egress,
                }
                for item, path in zip(source.classes, paths, strict=True)
            ],
            "exact_translations": {
                "MODEFAC": "RUNFACTOR",
                "SKIPMODES": "DELMODE",
                "access_and_egress_class": "DELACCESSMODE and DELEGRESSMODE",
                "IWAITFAC_and_XWAITFAC": "WAITFACTOR applied to all transit stop nodes",
                "half_headway": "IWAITCURVE and XWAITCURVE reference SYSTEMI wait curve 1",
            },
            "not_directly_translated": {
                "BOARDPEN": "TRNBUILD varies penalty by boarding number; PT BRDPEN varies by transit mode and cannot reproduce the vector exactly.",
                "IWAITMAX": "TM1 caps initial wait for selected ferry and commuter-rail modes; PT wait-curve selection is node-based, not mode-based.",
                "NOX": "TRNBUILD prohibits arbitrary mode-to-mode movements; PT access/egress restrictions cover the user-class choice, but the full support-mode table needs Task 3 route testing.",
                "COMBINE": "TRNBUILD line-combination rules have no one-to-one FACTORS keyword; PT service-frequency route choice must be tested in Task 3.",
                "drive_link_selection": "TM1 conditionally reads PNR link files by path class; Task 3 must preserve this availability when constructing or selecting the PT network.",
            },
            "assignment_script_settings": [
                "USERCLASSES and FACTORI file bindings",
                "demand-matrix bindings",
                "time-period network and line selection",
                "maximum route/path limits and output controls",
                "fare-system bindings",
            ],
        }

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        temporary_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(content)
            temporary_path.replace(path)
        except OSError as error:
            raise OutputWriteError(f"Could not write PT factor output {path}: {error}") from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


def _run_factors(factors: tuple[ModeFactor, ...]) -> str:
    return ",".join(f"{item.count}*{_decimal(item.factor)}" for item in factors)


def _ranges(ranges: tuple[tuple[int, int], ...]) -> str:
    return ",".join(str(first) if first == last else f"{first}-{last}" for first, last in ranges)


def _values(values: tuple[int, ...]) -> str:
    return ",".join(str(value) for value in values)


def _decimal(value: Decimal) -> str:
    return format(value, "f")

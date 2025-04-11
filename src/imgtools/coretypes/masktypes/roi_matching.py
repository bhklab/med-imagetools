from __future__ import annotations

import re
from collections import defaultdict
from enum import Enum
from functools import lru_cache
from itertools import product
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator

from imgtools.loggers import logger

__all__ = [
    "ROIMatcher",
    "ROIMatchStrategy",
    "handle_roi_matching",
]


# we should rename this to be intuitive
class ROIMatchStrategy(str, Enum):  # noqa: N801
    """Enum for ROI handling strategies."""

    # merge all ROIs with the same key
    MERGE = "merge"

    # for each key, keep the first ROI found based on the pattern
    KEEP_FIRST = "keep_first"

    # separate all ROIs
    SEPARATE = "separate"


PatternString = str
ROIGroupPatterns = dict[str, list[PatternString]]

Valid_Inputs = (
    ROIGroupPatterns
    | dict[str, PatternString]
    | list[PatternString]
    | PatternString
    | None
)
"""These are the valid inputs for the ROI matcher.
1) A dictionary with keys as strings and values as lists of regex patterns.
2) A dictionary with keys as strings and value as a single (str) regex pattern.
2) A list of regex patterns.
3) A single regex pattern as a string.
"""


class ROIMatcher(BaseModel):
    match_map: Annotated[
        ROIGroupPatterns,
        Field(description="Flexible input for ROI matcher"),
    ]
    handling_strategy: ROIMatchStrategy = ROIMatchStrategy.MERGE
    ignore_case: bool = True
    default_key: ClassVar[str] = "ROI"

    @field_validator("match_map", mode="before")
    @classmethod
    def match_map(cls, v: Valid_Inputs) -> ROIGroupPatterns:
        if not v:
            logger.debug(f"Empty ROI map provided {v=} . Defaulting to .*")
            return {cls.default_key: [".*"]}

        match v:
            case dict():
                cleaned = {}
                for k, val in v.items():
                    if isinstance(val, str):
                        cleaned[k] = [val]
                    elif isinstance(val, list):
                        cleaned[k] = val
                    else:  # pragma: no cover
                        msg = f"Invalid type for key '{k}': {type(val)}"
                        raise TypeError(msg)
                return cleaned
            case list():
                return {cls.default_key: v}
            case str():
                return {cls.default_key: [v]}
            case _:  # pragma: no cover
                msg = f"Unrecognized ROI matching input type: {type(v)}"
                raise TypeError(msg)

    def match_rois(self, roi_names: list[str]) -> list[tuple[str, list[str]]]:
        """
        Match ROI names against the provided patterns.

        Parameters
        ----------
        roi_names : list[str]
            List of ROI names to match.

        Returns
        -------
        list[tuple[str, list[str]]]
            List of tuples containing the key and matched ROI names.
            See `handle_roi_matching` for notes on the handling strategies.

        See Also
        --------
        handle_roi_matching : Function to handle the matching logic.
        """
        return handle_roi_matching(
            roi_names,
            self.match_map,
            self.handling_strategy,
            ignore_case=self.ignore_case,
        )


def handle_roi_matching(
    roi_names: list[str],
    roi_matching: ROIGroupPatterns,
    strategy: ROIMatchStrategy,
    ignore_case: bool = True,
) -> list[tuple[str, list[str]]]:
    """
    Match ROI names against regex patterns and apply a handling strategy.

    Parameters
    ----------
    roi_names : list[str]
        List of ROI names to match.
    roi_matching : ROIGroupPatterns
        Mapping of keys to list of regex patterns.
    strategy :ROIMatchStrategy
        Strategy to use: MERGE, KEEP_FIRST, or SEPARATE.
    ignore_case : bool
        Whether to ignore case during matching.

    Returns
    -------
    list[tuple[str, list[str]]]
        List of tuples containing the key and matched ROI names.
        See Notes for details on the handling strategies.

    Notes
    -----
    - MERGE: Merge all ROIs with the same key. Returns a single tuple for each key,
        but the value is a list of all the matched ROIs.
        i.e [('GTV', ['GTV1', 'GTV2']), ('PTV', ['PTV1', 'ptv x'])]
    - KEEP_FIRST: For each key, keep the first ROI found based on the pattern.
        Returns a single tuple for each key, but the value is a list of size ONE with
        the first matched ROI.
        i.e [('GTV', ['GTV1']), ('PTV', ['PTV1'])]
    - SEPARATE: Separate all ROIs. Returns possibly multiple tuples for each key,
        because a key may have multiple ROIs matching the pattern.
        i.e [('GTV', ['GTV1']), ('GTV', ['GTV2']), ('PTV', ['PTV1'])]
    """
    flags = re.IGNORECASE if ignore_case else 0

    @lru_cache(maxsize=128)
    def _match_pattern(roi_name: str, pattern: PatternString) -> bool:
        return re.fullmatch(pattern, roi_name, flags=flags) is not None

    results = defaultdict(list)

    for key, patterns in roi_matching.items():
        for pattern, roi_name in product(patterns, roi_names):
            if _match_pattern(roi_name, pattern):
                results[key].append(roi_name)

    match strategy:
        case ROIMatchStrategy.MERGE:
            # Merge all ROIs with the same key
            # this means that we return a single tuple for each key
            # but the value is a list of all the matched ROIs
            return [(key, v) for key, v in results.items() if v]
        case ROIMatchStrategy.KEEP_FIRST:
            # For each key, keep the first ROI found based on the pattern
            # this means that we return a single tuple for each key
            # but the value is a list of size ONE with the first matched ROI
            return [(key, [v[0]]) for key, v in results.items() if v]
        case ROIMatchStrategy.SEPARATE:
            # Separate all ROIs
            # this means that we possibly return a MULTIPLE tuples for each key
            # because a key may have multiple ROIs matching the pattern
            tuples = []
            for key, v in results.items():
                for roi in v:
                    tuples.append((key, [roi]))
            return tuples
        case _:  # pragma: no cover
            errmsg = (
                f"Unrecognized strategy: {strategy}. Something went wrong."
            )
            raise ValueError(errmsg)


if __name__ == "__main__":  # pragma: no cover
    from pathlib import Path
    from typing import (
        Type,
    )

    from pydantic_settings import (
        BaseSettings,
        PydanticBaseSettingsSource,
        SettingsConfigDict,
        # TomlConfigSettingsSource,
        YamlConfigSettingsSource,
    )
    from rich import print  # noqa

    class Settings(BaseSettings):
        rois: ROIMatcher = ROIMatcher(match_map={"ROI": [".*"]})

        model_config = SettingsConfigDict(
            # to instantiate the Login class, the variable name would be login.nbia_username in the environment
            # env_nested_delimiter="__",
            # env_file=".env",
            # env_file_encoding="utf-8",
            yaml_file=(Path().cwd() / "imgtools.yaml",),
            # allow for other fields to be present in the config file
            # this allows for the config file to be used for other purposes
            # but also for users to define anything else they might want
            extra="ignore",
        )

        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                YamlConfigSettingsSource(settings_cls),
            )

        @property
        def json_schema(self) -> dict:
            """Return the JSON schema for the settings."""
            return self.model_json_schema()

        @classmethod
        def from_user_yaml(cls, path: Path) -> Settings:
            """Load settings from a YAML file."""
            source = YamlConfigSettingsSource(cls, yaml_file=path)
            settings = source()
            return cls(**settings)

        def to_yaml(self, path: Path) -> None:
            """Return the YAML representation of the settings."""
            import yaml  # type: ignore

            model = self.model_dump(mode="json")
            with path.open("w") as f:
                yaml.dump(model, f, sort_keys=False)

    settings = Settings()
    print(settings)

    matcher = ROIMatcher(
        match_map={
            "GTV": ["GTV.*"],
            "PTV": ["PTV.*"],
            "CTV": ["CTV.*"],
        }
    )
    print(matcher)

    settings.to_yaml(Path("imgtools_settings.yaml"))

    print(Settings.from_user_yaml(Path("imgtools_settings3.yaml")))

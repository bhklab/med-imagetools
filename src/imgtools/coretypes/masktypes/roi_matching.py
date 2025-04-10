from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator


# we should rename this to be intuitive
class ROI_HANDLING(str, Enum):  # noqa: N801
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


class ROIMatcher(BaseModel):
    roi_map: Annotated[
        ROIGroupPatterns,
        Field(description="Flexible input for ROI matcher"),
    ]
    handling_strategy: ROI_HANDLING = ROI_HANDLING.MERGE
    ignore_case: bool = True
    default_key: ClassVar[str] = "ROI"

    @field_validator("roi_map", mode="before")
    @classmethod
    def validate_roi_map(cls, v: Valid_Inputs) -> ROIGroupPatterns:
        match v:
            case dict():
                if not v:
                    return {cls.default_key: [".*"]}
                cleaned = {}
                for k, val in v.items():
                    if isinstance(val, str):
                        cleaned[k] = [val]
                    elif isinstance(val, list):
                        cleaned[k] = val
                    else:
                        msg = f"Invalid type for key '{k}': {type(val)}"
                        raise TypeError(msg)
                return cleaned
            case list():
                return {cls.default_key: v}
            case str():
                return {cls.default_key: [v]}
            case None:
                return {cls.default_key: [".*"]}
            case _:  # pragma: no cover
                msg = f"Unrecognized ROI matching input type: {type(v)}"
                raise TypeError(msg)


def match_roi(
    roi_names: list[str],  # assumes already sorted
    roi_matching: ROIGroupPatterns,
    ignore_case: bool,
) -> dict[str, list[str]]:
    results = defaultdict(list)
    key: str
    patterns: list[PatternString]
    flags = re.IGNORECASE if ignore_case else 0

    def _match_pattern(roi_name: str, pattern: PatternString) -> bool:
        return re.fullmatch(pattern, roi_name, flags=flags) is not None

    # this unfortunately not really efficient, can use lru_cache
    # but we don't need to optimize this for now
    for key, patterns in roi_matching.items():
        for pattern, roi_name in product(patterns, roi_names):
            if _match_pattern(roi_name, pattern):
                results[key].append(roi_name)

    # filter out any potential empty lists
    return {k: v for k, v in results.items() if v}


@dataclass
class ROIMatchResult:
    key: str
    matches: list[str]  # can be many if MERGE
    strategy: ROI_HANDLING


def handle_roi_matching(
    roi_names: list[str],
    roi_matching: ROIGroupPatterns,
    strategy: ROI_HANDLING,
    ignore_case: bool = True,
) -> list[ROIMatchResult]:
    """
    Apply a matching strategy to ROI names using regex-based matching rules.

    Parameters
    ----------
    roi_names : list[str]
        List of ROI names to match.
    roi_matching : dict[str, list[str]]
        Mapping of label key to regex patterns or exact names.
    strategy : ROI_HANDLING
        Strategy for combining matches (MERGE, KEEP_FIRST, SEPARATE).
    ignore_case : bool
        Whether to ignore case when matching (default: True)

    """
    matched = match_roi(roi_names, roi_matching, ignore_case=ignore_case)
    output: list[ROIMatchResult] = []

    if strategy == ROI_HANDLING.SEPARATE:
        for key, matches in matched.items():
            for match in matches:
                output.append(
                    ROIMatchResult(key=key, matches=[match], strategy=strategy)
                )
    elif strategy == ROI_HANDLING.MERGE:
        for key, matches in matched.items():
            output.append(
                ROIMatchResult(key=key, matches=matches, strategy=strategy)
            )
    elif strategy == ROI_HANDLING.KEEP_FIRST:
        for key, matches in matched.items():
            output.append(
                ROIMatchResult(
                    key=key, matches=[matches[0]], strategy=strategy
                )
            )
    else:  # pragma: no cover
        errmsg = f"Unrecognized strategy: {strategy}. Something went wrong."
        raise ValueError(errmsg)

    return output


if __name__ == "__main__":
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
        rois: ROIMatcher = ROIMatcher(roi_map={"ROI": [".*"]})

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
        roi_map={
            "GTV": ["GTV.*"],
            "PTV": ["PTV.*"],
            "CTV": ["CTV.*"],
        }
    )
    print(matcher)

    settings.to_yaml(Path("imgtools_settings.yaml"))

    print(Settings.from_user_yaml(Path("imgtools_settings3.yaml")))

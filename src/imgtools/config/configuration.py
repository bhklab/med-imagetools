from __future__ import annotations

from pathlib import Path
from typing import Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    # TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)

from imgtools.io.sample_input import SampleInput
from imgtools.io.sample_output import SampleOutput


class MedImageToolsSettings(BaseSettings):
    """
    Central configuration class for MedImageTools settings.

    This class provides a standardized way to manage settings for medical image processing,
    supporting YAML configuration files and programmatic configuration.

    """

    # Use a complete default instance rather than default_factory
    input: SampleInput = Field(
        default_factory=SampleInput.default,
        description="Configuration for sample input handling and processing",
    )
    output: SampleOutput = Field(
        default_factory=SampleOutput.default,
        description="Configuration for sample output handling and processing",
    )
    model_config = SettingsConfigDict(
        yaml_file=(Path().cwd() / "imgtools.yaml",),
        # allow for other fields to be present in the config file
        # this allows for the config file to be used for other purposes
        # but also for users to define anything else they might want
        extra="ignore",
        # in the future we can automatically generate CLI parsers
        # cli_parse_args=True,
        # cli_use_class_docs_for_groups=True,  # optional: show nested class docstrings as CLI headings
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
    def from_user_yaml(cls, path: Path) -> MedImageToolsSettings:
        """Load settings from a YAML file."""
        source = YamlConfigSettingsSource(cls, yaml_file=path)
        settings = source()
        return cls(**settings)

    def to_yaml(self, path: Path) -> None:
        """Return the YAML representation of the settings."""
        import yaml  # type: ignore

        model = self.model_dump(mode="json")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                yaml.dump(model, f, sort_keys=False)
        except (OSError, IOError) as e:
            msg = f"Failed to save settings to {path}: {e}"
            raise ValueError(msg) from e


# if __name__ == "__main__":
#     from rich import print  # noqa
#     from imgtools.io.sample_input import (
#         ROIMatcher,
#         ROIMatchStrategy,
#         ROIMatchFailurePolicy,
#     )

#     config = MedImageToolsSettings(
#         input=SampleInput(
#             directory=Path("data/RADCURE"),
#             update_crawl=False,
#             n_jobs=12,
#             modalities=["CT", "RTSTRUCT"],
#             roi_matcher=ROIMatcher(
#                 match_map={
#                     "GTV": ["GTVp"],
#                     "NODES": ["GTVn_.*"],
#                     "LPLEXUS": ["BrachialPlex_L"],
#                     "RPLEXUS": ["BrachialPlex_R"],
#                     "BRAINSTEM": ["Brainstem"],
#                     "LACOUSTIC": ["Cochlea_L"],
#                     "RACOUSTIC": ["Cochlea_R"],
#                     "ESOPHAGUS": ["Esophagus"],
#                     "LEYE": ["Eye_L"],
#                     "REYE": ["Eye_R"],
#                     "LARYNX": ["Larynx"],
#                     "LLENS": ["Lens_L"],
#                     "RLENS": ["Lens_R"],
#                     "LIPS": ["Lips"],
#                     "MANDIBLE": ["Mandible_Bone"],
#                     "LOPTIC": ["Nrv_Optic_L"],
#                     "ROPTIC": ["Nrv_Optic_R"],
#                     "CHIASM": ["OpticChiasm"],
#                     "LPAROTID": ["Parotid_L"],
#                     "RPAROTID": ["Parotid_R"],
#                     "CORD": ["SpinalCord"],
#                 },
#                 allow_multi_key_matches=False,  # if True, an ROI can match multiple keys
#                 handling_strategy=ROIMatchStrategy.SEPARATE,
#                 ignore_case=True,
#                 on_missing_regex=ROIMatchFailurePolicy.WARN,
#             ),
#         )
#     )
#     print(config)

#     # # config.input.print_tree()

#     # # print(config.input.query("CT,RTSTRUCT"))

#     import json

#     with open("med-imgtools_jsonschema.json", "w") as f:  # noqa: PTH123
#         json.dump(config.json_schema, f, indent=4)

#     # config.to_yaml(Path("imgtools.yaml"))

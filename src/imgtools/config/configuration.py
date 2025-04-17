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

from imgtools.io.loaders.sample_input import SampleInput


class MedImageToolsSettings(BaseSettings):
    """
    Central configuration class for MedImageTools settings.

    This class provides a standardized way to manage settings for medical image processing,
    supporting YAML configuration files and programmatic configuration.

    Attributes
    ----------
    input : SampleInput
        Configuration for sample input handling and processing

    Examples
    --------
    >>> from imgtools.config.configuration import (
    ...     MedImageToolsSettings,
    ... )
    >>> config = MedImageToolsSettings()
    >>> config.input.dataset_name
    """

    # use default() classmethod to set default values
    input: SampleInput = Field(
        default_factory=SampleInput.default,
        description="Configuration for sample input handling and processing",
    )
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


if __name__ == "__main__":
    from rich import print  # noqa

    config = MedImageToolsSettings()
    print(config)

    config.input.print_tree()

    print(config.input.query("CT,RTSTRUCT"))

    import json

    with open("imgtools.json", "w") as f:  # noqa: PTH123
        json.dump(config.json_schema, f, indent=4)

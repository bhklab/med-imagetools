from pathlib import Path
from typing import Literal, Tuple, Type

import click
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import (
	BaseSettings,
	PydanticBaseSettingsSource,
	SettingsConfigDict,
)
from pydantic_settings.sources import YamlConfigSettingsSource


class ProcessSettings(BaseModel):
	resample: bool = Field(default=False, description="Whether to resample DICOMs")
	filter_modality: Literal["CT", "MR", "PT"] | None = Field(
		default=None, description="Only process DICOMs with this modality"
	)


class TrainSettings(BaseModel):
	epochs: int = Field(default=10)
	model_name: str = Field(default="unet")
	output_dir: Path | None = Field(default=None)


class Settings(BaseSettings):
	log_level: str = Field(default="INFO")
	data_dir: Path
	process: ProcessSettings = Field(default_factory=ProcessSettings)
	train: TrainSettings = Field(default_factory=TrainSettings)

	model_config = SettingsConfigDict(
		yaml_file="config.yaml",
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
	) -> Tuple[PydanticBaseSettingsSource, ...]:
		return (
			init_settings,
			YamlConfigSettingsSource(settings_cls),
		)


def safe_init_settings(**kwargs) -> Settings:
	try:
		return Settings(**kwargs)
	except ValidationError as e:
		click.secho("❌ Missing or invalid configuration values:", fg="red", bold=True)
		for err in e.errors():
			field = ".".join(str(p) for p in err["loc"])
			msg = err["msg"]
			click.secho(f"  - {field}: {msg}", fg="yellow")
		click.echo("\n💡 Hint: Use CLI flags or define missing values in `config.yaml`.")
		raise click.Abort()


@click.group()
def cli():
	"""A CLI for medical imaging workflows."""

@cli.command()
@click.option("--log-level", default=None)
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--resample", is_flag=True, default=None)
@click.option("--filter-modality", type=click.Choice(["CT", "MR", "PT"]), default=None)
def process(log_level, data_dir, resample, filter_modality):
	overrides = {
		k: v for k, v in locals().items() if v is not None
	}

	settings = safe_init_settings(**overrides)
	click.echo(f"[process] Log level: {settings.log_level}")
	click.echo(f"[process] Data dir: {settings.data_dir}")
	click.echo(f"[process] Resample: {settings.process.resample}")
	click.echo(f"[process] Modality Filter: {settings.process.filter_modality}")


@cli.command()
@click.option("--log-level", default=None)
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--epochs", type=int, default=None)
@click.option("--model-name", type=str, default=None)
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def train(log_level, data_dir, epochs, model_name, output_dir):
	overrides = {
		k: v for k, v in dict(log_level=log_level, data_dir=data_dir).items() if v is not None
	}
	if epochs or model_name or output_dir:
		overrides["train"] = TrainSettings(
			epochs=epochs or 10,
			model_name=model_name or "unet",
			output_dir=output_dir or Path("./output"),
		)

	settings = safe_init_settings(**overrides)
	click.echo(f"[train] Epochs: {settings.train.epochs}")
	click.echo(f"[train] Model: {settings.train.model_name}")
	click.echo(f"[train] Output: {settings.train.output_dir}")


if __name__ == "__main__":
	cli()
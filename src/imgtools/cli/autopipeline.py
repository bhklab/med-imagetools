from pathlib import Path
import click
from imgtools.loggers import logger
from imgtools import BetaPipeline

@click.command()
@click.argument(
    "input_directory",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
        resolve_path=True,
        exists=True,
    ),
    help="Path to the input directory",
)
@click.argument(
    "output_directory",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
        resolve_path=True,
    ),
    help="Path to the output directory",
)
@click.option(
    "--modalities",
    default="CT",
    type=str,
    help="Modalities to process as a comma separated string",
)
@click.option("--spacing", default=[1.0, 1.0, 0.0], type=tuple)
def autopipeline(
    input_directory: Path,
    output_directory: Path,
    modalities: str,
    spacing: tuple,
) -> None:
    logger.debug("Running BetaPipeline via cli with args: %s", locals())\
    # paths will be resolved and validated by click params

    # validate modalities
    valid_modalities = ["CT", "MR", "PT", "RTSTRUCT", "RTDOSE", "RTPLAN"]
    mods = set([mod.strip().upper() for mod in modalities.split(",")])
    if not all([mod in valid_modalities for mod in mods]):
        bad_modalities = mods - set(valid_modalities)
        errmsg = (
            "Invalid modalities provided: %s. Valid modalities are: %s"
            % (bad_modalities, valid_modalities)
        )
        logger.error(errmsg)
        raise ValueError(errmsg)
    
    autopipe = BetaPipeline(
        input_directory=input_directory,
        output_directory=output_directory,
        query=modalities,
        spacing=spacing
    )
    autopipe.run()

if __name__ == "__main__":
    autopipeline()
import click
from pydanclick import from_pydantic

from .configuration import MedImageToolsSettings


@click.command()
@from_pydantic("settings", MedImageToolsSettings, ignore_unsupported=True)
def main(settings: MedImageToolsSettings) -> None:
    from rich import print  # noqa: A004

    print(settings)


if __name__ == "__main__":
    main()

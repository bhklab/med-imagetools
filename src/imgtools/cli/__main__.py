"""Command-line interface for the med-imagetools package.

This module sets up the command-line interface (CLI) for the med-imagetools package
using Click. The CLI is organized into command groups that are registered with a
CommandRegistry and displayed in organized sections using SectionedGroup.

How to use this system:
1. To add a new command group:
   - Use registry.create_group("group-name", "Group description")

2. To add a new command to an existing group:
   - Implement your command as a Click command function
   - Register it with registry.add("group-name", your_command)

3. Command implementation pattern:
   - Define your command using @click.command() and appropriate Click options
   - Register it in the appropriate section in this file

Example of adding a new command:
    
    @click.command()
    @click.argument("input_path")
    @click.option("--output", "-o", help="Output file")
    def my_command(input_path, output):
        '''My command description.'''
        # Command implementation here
        pass
    
    # Then register it
    registry.create_group("my-tools", "My custom tools")
    registry.add("my-tools", my_command)
"""

import click

from imgtools import __version__

from . import set_log_verbosity
from .autopipeline import autopipeline
from .dicomfind import dicomfind
from .dicomshow import dicomshow
from .dicomsort import dicomsort

from .index import index
from .interlacer import interlacer
from .nnunet_pipeline import nnunet_pipeline

from .sectioned_group import SectionedGroup, CommandRegistry
from .testdatasets import testdata

# Create a shared registry
registry = CommandRegistry()

# Register groups and commands
registry.create_group("core commands", "Main subcommands for the med-imagetools package.")
registry.add('core commands', index)
registry.add('core commands', interlacer)
registry.add('core commands', autopipeline)
registry.add('core commands', nnunet_pipeline)

registry.create_group("utilities", "Tools for working with DICOM files.")
registry.add("utilities", dicomfind)
registry.add("utilities", dicomsort)
registry.add("utilities", dicomshow)


if not testdata.hidden:
    registry.create_group("testing", "Datasets for testing and tutorials.")
    registry.add("testing", testdata)


@click.group(cls=SectionedGroup, registry=registry, no_args_is_help=True)
@set_log_verbosity()
@click.version_option(
    version=__version__,
    package_name="med-imagetools",
    prog_name="imgtools",
    message="%(package)s:%(prog)s:%(version)s",
)
@click.help_option("-h", "--help")
def cli(verbose: int, quiet: bool) -> None:
    """A collection of tools for working with medical imaging data."""
    # Notes
    # -----
    # This function serves as the main entry point for the command-line interface.
    # It configures logging verbosity and sets up the command groups.
    
    # For developers: To extend this CLI, register your commands with the registry
    # object using the pattern shown in this file.
    pass

cli.add_registry(registry)

@click.command(name="shell-completion", hidden=True)
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
@click.pass_context
def shell_completion(ctx: click.Context, shell: str) -> None:
    """Emit shell completion script (hidden command).
    
    This command generates a shell completion script for the specified shell.
    Supported shells: bash, zsh, fish.
    """
    # validate the shell argument
    if shell not in ["bash", "zsh", "fish"]:
        raise click.BadParameter(f"Unsupported shell: {shell}. Supported: bash, zsh, fish")

    # Generate the completion script
    command = ["_IMGTOOLS_COMPLETE={}_source imgtools".format(shell)]
    import subprocess

    # Generate the completion script using subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        click.echo(result.stdout)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error generating completion script: {e}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
    

cli.add_command(shell_completion)

if __name__ == "__main__":
    cli()
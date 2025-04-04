# sectioned_group.py

from __future__ import annotations

from click import Group, Command
from typing import TYPE_CHECKING
from .command_registry import CommandRegistry

if TYPE_CHECKING:
    from click import Context, HelpFormatter

class SectionedGroup(Group):
    """A Click Group that supports subcommand groupings via a CommandRegistry.
    
    This class extends Click's Group to provide organized command sections in the 
    help output. Commands are grouped into named sections with descriptions, 
    making the CLI help more organized and user-friendly.
    
    Parameters
    ----------
    *args
        Arguments to pass to the Click Group constructor.
    registry : CommandRegistry, optional
        Registry containing command groups and their commands.
    **kwargs
        Keyword arguments to pass to the Click Group constructor.
        
    Notes
    -----
    Developers should not typically need to instantiate this class directly.
    Instead, use it as the `cls` parameter when creating a Click group:
    
    ```python
    @click.group(cls=SectionedGroup, registry=my_registry)
    def cli():
        '''CLI description'''
        pass
    ```
    
    Then register commands via the registry and add them with:
    
    ```python
    cli.add_registry(my_registry)
    ```
    """

    def __init__(self, *args, registry: CommandRegistry | None = None, **kwargs): # type: ignore
        super().__init__(*args, **kwargs)
        self._registry = registry or CommandRegistry()

    def add_registry(self, registry: CommandRegistry) -> None:
        """Assign a registry and register all commands from it.
        
        This method associates a CommandRegistry with this group and adds all
        commands from the registry to the Click group.
        
        Parameters
        ----------
        registry : CommandRegistry
            The registry containing command groups to add to this Click group.
            
        Notes
        -----
        This should be called after defining the main CLI function and all
        commands have been registered with the registry.
        """
        self._registry = registry
        for group in registry.groups().values():
            for cmd in group.commands:
                self.add_command(cmd)

    def format_commands(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Format commands into sectioned groups in the help output.
        
        Overrides the default help formatter to display commands organized by
        their groups with group descriptions as section headers.
        
        Parameters
        ----------
        ctx : Context
            The Click context.
        formatter : HelpFormatter
            The formatter to write to.
            
        Notes
        -----
        This method is called automatically by Click when generating help text.
        Developers don't need to call this method directly.
        """
        if not self._registry.groups():
            # No groups to display
            return
        
        # print out a header
        formatter.write_paragraph()
        formatter.write(f"{'':>{formatter.current_indent}}AVAILABLE COMMANDS:\n")


        for group in self._registry.groups().values():
            if not group.commands: # Skip empty groups
                continue
            rows = []
            limit = formatter.width - 6 - max(len(cmd.name) for cmd in group.commands if cmd.name is not None)
            for cmd in group.commands:
                if cmd.name is not None:
                    rows.append((cmd.name, cmd.get_short_help_str(limit)))
            
            # what to write in the section heading
            heading : str
            if group.description:
                heading = f"[{group.name.upper()}] {group.description}"
            else:
                heading = group.name
            heading_str = f"{'':>{formatter.current_indent}}{heading}\n"            
            formatter.write_paragraph()
            formatter.write(heading_str)
            formatter.indent()
            formatter.write_dl(rows)
            formatter.dedent()
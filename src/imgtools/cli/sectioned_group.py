# sectioned_group.py

from __future__ import annotations

from click import Group, Command
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from click import Context, HelpFormatter

@dataclass
class CommandGroup:
    """Represents a command group with an optional description.
    
    A CommandGroup organizes related commands together under a single named
    section in the CLI help output.
    
    Parameters
    ----------
    name : str
        The name of the command group.
    description : str, optional
        A brief description of the command group's purpose.
    commands : list[Command], optional
        A list of Click commands belonging to this group.
        
    Notes
    -----
    Developers should not create CommandGroup instances directly.
    Instead, use CommandRegistry.create_group() to create new command groups.
    """
    name: str
    description: Optional[str] = None
    commands: list[Command] = field(default_factory=list)

@dataclass
class CommandRegistry:
    """Registry mapping section name to command groups.
    
    This class manages command groups and provides methods to create groups
    and add commands to those groups. It centralizes command organization
    for the CLI.
    
    Parameters
    ----------
    _groups : dict, optional
        Internal dictionary mapping group names to CommandGroup objects.
        
    Notes
    -----
    Developers should use this class as follows:
    
    1. Create a registry instance:
       ```python
       registry = CommandRegistry()
       ```
       
    2. Define command groups:
       ```python
       registry.create_group("my-tools", "Tools for my specific purpose")
       ```
       
    3. Add commands to groups:
       ```python
       # where my_command is a Click command function
       registry.add("my-tools", my_command)
       ```
       
    4. Use with SectionedGroup:
       ```python
       @click.group(cls=SectionedGroup, registry=registry)
       def cli():
           '''CLI description'''
           pass
           
       cli.add_registry(registry)
       ```
    """
    _groups: dict[str, CommandGroup] = field(default_factory=dict)

    def create_group(self, name: str, description: Optional[str] = None) -> None:
        """Create a new command group with optional description.
        
        Parameters
        ----------
        name : str
            The name of the group to create.
        description : str, optional
            A brief description of the group's purpose.
            
        Raises
        ------
        ValueError
            If a group with the given name already exists.
            
        Examples
        --------
        >>> registry = CommandRegistry()
        >>> registry.create_group("conversion", "File conversion utilities")
        """
        if name in self._groups:
            raise ValueError(f"Group '{name}' already exists")
        self._groups[name] = CommandGroup(name=name, description=description)

    def add(self, group: str, cmd: Command) -> None:
        """Add a command to an existing group.
        
        Parameters
        ----------
        group : str
            The name of the group to add the command to.
        cmd : Command
            The Click command to add to the group.
            
        Raises
        ------
        ValueError
            If the specified group does not exist.
            
        Examples
        --------
        >>> @click.command()
        >>> def convert_file(filepath):
        >>>     '''Convert a file.'''
        >>>     pass
        >>> 
        >>> registry.add("conversion", convert_file)
        """
        if group not in self._groups:
            raise ValueError(f"Group '{group}' does not exist. Create it first using create_group()")
        self._groups[group].commands.append(cmd)

    def groups(self) -> dict[str, CommandGroup]:
        """Return all command groups.
        
        Returns
        -------
        dict
            Dictionary mapping group names to CommandGroup objects.
            
        Notes
        -----
        This method is primarily used internally by SectionedGroup to format
        help output, but can be useful for inspecting the current registry state.
        """
        return self._groups

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

    def __init__(self, *args, registry: CommandRegistry | None = None, lazy_subcommands: dict | None =None, **kwargs): # type: ignore
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
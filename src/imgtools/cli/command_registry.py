"""Registry system for organizing CLI commands into logical groups.

This module provides the infrastructure for organizing Click commands into
named groups with descriptions, which improves the organization and readability
of CLI help output.
"""

from dataclasses import dataclass, field
from typing import Optional

import click

Command = click.Command

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
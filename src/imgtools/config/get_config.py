import os
import pathlib
import sys
import argparse

class ConfigPathError(Exception):
    """Custom exception for configuration path errors."""
    pass


class ConfigManager:
    def __init__(self, app_name: str, extension: str = "toml", force_posix: bool = False, roaming: bool = False):
        """
        Initializes the ConfigManager for an application.

        Parameters:
        - app_name (str): Name of the application.
        - extension (str): Configuration file extension (default: "toml").
        - force_posix (bool): Force POSIX-style paths (`~/.app_name`).
        - roaming (bool): Use roaming profile on Windows (default: False).
        """
        if not app_name or not isinstance(app_name, str):
            raise ConfigPathError("Invalid app_name. Must be a non-empty string.")
        
        self.app_name = app_name
        self.extension = extension
        self.force_posix = force_posix
        self.roaming = roaming
        self._app_name_posix = self._posixify(app_name)
        self._platform = sys.platform

    def _posixify(self, name: str) -> str:
        """Convert app name to POSIX-friendly format."""
        return name.lower().replace(" ", "_")

    def get_app_config_dir(self) -> pathlib.Path:
        """
        Returns the base global configuration directory for the application.

        Raises:
        - ConfigPathError: If the path cannot be determined.
        """
        if self._platform.startswith("win32"):
            key = "APPDATA" if self.roaming else "LOCALAPPDATA"
            folder = os.environ.get(key)
            if folder:
                return pathlib.Path(folder,self._app_name_posix).expanduser() / 
            return pathlib.Path.home()

        if self.force_posix:
            return pathlib.Path.home() / f".{self._app_name_posix}"
        elif self._platform == "darwin":
            return pathlib.Path.home() / "Library" / "Application Support" / self.app_name

        xdg_config_home = os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")
        return pathlib.Path(xdg_config_home) / self._app_name_posix

    def get_config_files(self) -> dict:
        """
        Finds both local and global configuration files for the application.

        Returns:
        - dict: A dictionary with keys "local" and "global" containing Path objects to the config files,
                and their existence status.
        """
        file_name = f"{self._app_name_posix}.{self.extension}"

        # Local configuration file
        local_config_envvar = f"{self._app_name_posix.upper()}_CONFIG"
        local_config_env = os.environ.get(local_config_envvar)
        if local_config_env:
            local_config_path = pathlib.Path(local_config_env).expanduser()
        else:
            local_config_path = pathlib.Path.cwd() / file_name

        # Global configuration file
        global_config_envvar = f"{self._app_name_posix.upper()}_GLOBAL_CONFIG"
        global_config_env = os.environ.get(global_config_envvar)
        if global_config_env:
            global_config_path = pathlib.Path(global_config_env).expanduser()
        else:
            global_config_path = self.get_app_config_dir() / file_name

        return {
            "local": {"path": local_config_path, "exists": local_config_path.exists()},
            "global": {"path": global_config_path, "exists": global_config_path.exists()},
        }

    def explain_env_vars(self) -> str:
        """Provides an explanation of how users can set their own environment variables."""
        return (
            f"To override configuration file paths, you can set the following environment variables:\n"
            f"- Local configuration: Set {self._app_name_posix.upper()}_CONFIG to the full path of the desired local config file.\n"
            f"- Global configuration: Set {self._app_name_posix.upper()}_GLOBAL_CONFIG to the full path of the desired global config file.\n"
            f"If these environment variables are not set, default paths will be used."
        )


def main():
    parser = argparse.ArgumentParser(description="Manage application configuration files.")
    parser.add_argument("app_name", help="Name of the application")
    parser.add_argument("--extension", default="toml", help="Configuration file extension (default: 'toml')")
    parser.add_argument("--force-posix", action="store_true", help="Force using POSIX-style paths on all platforms")
    parser.add_argument("--roaming", action="store_true", help="Use roaming profile on Windows")
    args = parser.parse_args()

    # Initialize ConfigManager
    manager = ConfigManager(
        app_name=args.app_name,
        extension=args.extension,
        force_posix=args.force_posix,
        roaming=args.roaming,
    )

    # Retrieve config files
    config_files = manager.get_config_files()

    # Display configuration info
    print(f"Configuration info for application: {args.app_name}")
    print("\nLocal configuration file:")
    print(f"  Path: {config_files['local']['path']}")
    print(f"  Exists: {'Yes' if config_files['local']['exists'] else 'No'}")

    print("\nGlobal configuration file:")
    print(f"  Path: {config_files['global']['path']}")
    print(f"  Exists: {'Yes' if config_files['global']['exists'] else 'No'}")

    # Display environment variable instructions
    print("\nEnvironment Variable Overrides:")
    print(manager.explain_env_vars())




if __name__ == "__main__":
    main()

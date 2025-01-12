from __future__ import annotations
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any, Generator, NoReturn, Optional, Dict
from enum import Enum, auto
import SimpleITK as sitk
from contextlib import contextmanager
from imgtools.types import PathLike
from imgtools.io.pattern_parser import PatternResolver
from imgtools.logging import logger
from ..exceptions import DirectoryNotFoundError


class ExistingFileMode(Enum):
    """Enum to specify handling behavior for existing files."""

    # log as debug, and continue with the operation
    OVERWRITE = auto()

    # log as debug, and return None which should be handled appropriately by the caller
    SKIP = auto()

    # log as error, and raise a FileExistsError
    FAIL = auto()

    # log as warning, and continue with the operation
    RAISE_WARNING = auto()


@dataclass
class AbstractBaseWriter(ABC):
    """Abstract base class for managing file writing with customizable paths and filenames."""

    # Any subclass has to be initialized with a root directory and a filename format
    # Gets converted to a Path object in __post_init__
    root_directory: PathLike = field(
        metadata={"help": "Root directory where files will be saved."}
    )

    # The filename format string with placeholders for context variables
    # e.g. "{subject_id}_{date}/{disease}.txt"
    filename_format: str = field(
        metadata={
            "help": (
                "Format string defining the directory and filename structure. "
                "Supports placeholders for context variables. "
                "e.g. '{subject_id}_{date}/{disease}.txt'"
            )
        }
    )

    # optionally, you can set create_dirs to False if you want to handle the directory creation yourself
    create_dirs: bool = field(
        default=True,
        metadata={
            "help": "If True, creates necessary directories if they don't exist."
        },
    )

    # class-level pattern resolver instance shared across all instances

    existing_file_mode: ExistingFileMode = field(
        default=ExistingFileMode.FAIL,
        metadata={
            "help": "Behavior when a file already exists. Options: OVERWRITE, SKIP, FAIL, RAISE_WARNING."
        },
    )

    sanitize_filenames: bool = field(
        default=True,
        metadata={
            "help": "If True, replaces illegal characters from filenames with underscores."
        },
    )

    # Internal context storage for pre-checking
    context: Dict[str, Any] = field(default_factory=dict, init=False)

    # PatternResolver to handle filename formatting
    pattern_resolver: PatternResolver = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the writer with the given root directory and filename format."""
        self.root_directory = Path(self.root_directory)
        if self.create_dirs:
            self.root_directory.mkdir(parents=True, exist_ok=True)
        elif not self.root_directory.exists():
            msg = f"Root directory {self.root_directory} does not exist."
            raise DirectoryNotFoundError(msg)
        self.pattern_resolver = PatternResolver(self.filename_format)

        # if the existing_file_mode is a string, convert it to the Enum
        if isinstance(self.existing_file_mode, str):
            self.existing_file_mode = ExistingFileMode[self.existing_file_mode.upper()]

    @abstractmethod
    def save(self, *args: Any, **kwargs: Any) -> Path:  # noqa
        """Abstract method for writing data. Must be implemented by subclasses.

        Can use resolve_path() or resolve_and_validate_path() to get the output path.

        For efficiency, use self.context to access the context variables, updating
        them with the kwargs passed from the save method.

        This will help simplify repeated saves with similar context variables.
        """
        pass

    def set_context(self, **kwargs: Any) -> None:
        """Set the context for the writer."""
        self.context.update(kwargs)

    def _generate_datetime_strings(self) -> dict[str, str]:
        """Free to use date-time context values."""
        now = datetime.now(timezone.utc)
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H%M%S"),
            "date_time": now.strftime("%Y-%m-%d_%H%M%S"),
        }

    def resolve_path(self, **kwargs: Any) -> Path:  # noqa
        """Generate a file path based on the filename format, subject ID, and additional parameters."""
        save_context = {**self._generate_datetime_strings(), **self.context}
        save_context.update(kwargs)
        filename = self.pattern_resolver.resolve(save_context)
        if self.sanitize_filenames:
            filename = self._sanitize_filename(filename)
        out_path = self.root_directory / filename
        if self.create_dirs:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        return out_path

    def resolve_and_validate_path(self, **kwargs: Any) -> Optional[Path]:
        """Pre-resolve the output path and validate based on the existing file mode.

        Also stores the context for later use.
        Useful for pre-checking if saving is valid before heavy computations.

        Parameters
        ----------
        **kwargs : Any
            Additional parameters for filename formatting.

        Returns
        -------
        Optional[Path]
            Resolved path for the file or None if skipped.

        Raises
        ------
        FileExistsError
            If the file exists and the mode is FAIL.
        """
        out_path = self.resolve_path(**kwargs)
        self.set_context(**kwargs)
        logger.debug(f"Resolved path: {out_path} and {out_path.exists()=}")

        if out_path.exists():
            match self.existing_file_mode:
                case ExistingFileMode.SKIP:
                    logger.debug(f"File {out_path} exists. Skipping.")
                    return None
                case ExistingFileMode.FAIL:
                    raise FileExistsError(f"File {out_path} already exists.")
                case ExistingFileMode.RAISE_WARNING:
                    logger.warning(f"File {out_path} exists. Proceeding anyway.")
                case ExistingFileMode.OVERWRITE:
                    logger.debug(f"File {out_path} exists. Overwriting.")
        return out_path

    def validate_path(self, **kwargs: Any) -> Optional[Path]:
        """Pre-checking file existence and setting up the writer context.

        Main idea here is to allow users to save computation if they choose to skip existing files.
        i.e
        >>> if not writer.validate_path(subject="math", name="context_test"):
        >>>     continue

        The keyword arguments passed are also saved in the instance, so running .save() will use
        the same context, optionally can update the context with new values passed to .save().

        >>> if path := writer.validate_path(subject="math", name="context_test"):
                # do some expensive computation to generate the data you wish to save
                writer.save(data) # automatically uses the context set in validate_path

        Parameters
        ----------
        **kwargs : Any
            Parameters for resolving the filename and validating existence.

        Returns
        ------
        Path | None
            if the file exists and the mode is SKIP, returns None.
            if the file exists and the mode is FAIL, raises a FileExistsError.
            if the file exists and the mode is RAISE_WARNING, logs a warning and returns the path.
            if the file exists and the mode is OVERWRITE, logs a debug message and returns the path.

        Raises
        ------
        FileExistsError
            If the file exists and the mode is FAIL.
        """
        logger.debug("validate_path")
        try:
            logger.debug("try")
            resolved_path = self.resolve_and_validate_path(**kwargs)
        except FileExistsError as e:
            logger.exception(f"Error in {self.__class__.__name__} during pre-check.")
            raise e
        return resolved_path

    # Context Manager Implementation
    def __enter__(self) -> AbstractBaseWriter:
        """
        Enter the runtime context related to this writer.

        Useful if the writer needs to perform setup actions, such as
        opening connections or preparing resources.
        """
        logger.debug(f"Entering context manager for {self.__class__.__name__}")
        return self

    def __exit__(
        self: "BaseWriter",
        exc_type: Optional[type],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Exit the runtime context related to this writer.

        Parameters
        ----------
        exc_type : Optional[type]
            The exception type, if an exception was raised, otherwise None.
        exc_value : Optional[BaseException]
            The exception instance, if an exception was raised, otherwise None.
        traceback : Optional[Any]
            The traceback object, if an exception was raised, otherwise None.
        """
        if exc_type:
            logger.exception(
                f"Exception raised in {self.__class__.__name__} while in context manager.",
                exc_info=exc_value,
            )
        logger.debug(f"Exiting context manager for {self.__class__.__name__}")

        # if the root directory is empty, aka we created it but didn't write anything, delete it
        if (
            self.create_dirs
            and self.root_directory.exists()
            and not any(self.root_directory.iterdir())
        ):
            logger.debug(f"Deleting empty directory {self.root_directory}")
            self.root_directory.rmdir()  # remove the directory if it's empty

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to remove or replace bad characters.

        Parameters
        ----------
        filename : str
            The original filename.

        Returns
        -------
        str
            A sanitized filename safe for most file systems.
        """
        import re

        # Replace bad characters with underscores
        sanitized = re.sub(r'[<>:"\\|?*]', "_", filename)

        # Optionally trim leading/trailing spaces or periods
        sanitized = sanitized.strip(" .")

        return sanitized

    def put(self, *args, **kwargs) -> NoReturn:  # noqa
        """Accdidentally using put() instead of save() will raise a fatal error."""
        msg = (
            "Method put() is deprecated and will be removed in future versions. "
            "Please use AbstractBaseWriter.save() instead of the old BaseWriter.put()."
        )
        logger.fatal(msg)
        import sys

        sys.exit(1)


# stop ruff check here
# ruff: noqa
class BaseWriter:
    def __init__(self, root_directory, filename_format, create_dirs=True) -> None:
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        if create_dirs and not os.path.exists(self.root_directory):
            os.makedirs(self.root_directory)

    def put(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError

    def save(self, *args, **kwargs) -> Path:
        """not meant to be used with old BaseWriter, use AbstractBaseWriter.save() instead"""
        msg = (
            "Method save() is not implemented for this writer. "
            "Please use AbstractBaseWriter.save() instead of the old BaseWriter.save()."
        )
        logger.fatal(msg)
        import sys

        sys.exit(1)

    def _get_path_from_subject_id(self, subject_id, **kwargs):
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H%M%S")
        date_time = date + "_" + time
        out_filename = self.filename_format.format(
            subject_id=subject_id, date=date, time=time, date_time=date_time, **kwargs
        )
        out_path = Path(self.root_directory, out_filename)

        out_dir = out_path.parent
        if self.create_dirs:
            out_dir.mkdir(parents=True, exist_ok=True)

        return out_path


class BaseSubjectWriter(BaseWriter):
    def __init__(
        self,
        root_directory,
        filename_format="{subject_id}.nii.gz",
        create_dirs=True,
        compress=True,
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        self.compress = compress
        if os.path.exists(self.root_directory):
            # delete the folder called {subject_id} that was made in the original BaseWriter / the one named {label_or_image}
            if os.path.basename(os.path.dirname(self.root_directory)) == "{subject_id}":
                shutil.rmtree(os.path.dirname(self.root_directory))
            elif "{label_or_image}{train_or_test}" in os.path.basename(
                self.root_directory
            ):
                shutil.rmtree(self.root_directory)

    def put(
        self,
        subject_id,
        image,
        is_mask=False,
        nnunet_info=None,
        label_or_image: str = "images",
        mask_label: str = "",
        train_or_test: str = "Tr",
        **kwargs,
    ) -> None:
        if is_mask:
            # remove illegal characters for Windows/Unix
            badboys = r'<>:"/\|?*'
            for char in badboys:
                mask_label = mask_label.replace(char, "")

            # filename_format eh
            self.filename_format = (
                mask_label + ".nii.gz"
            )  # save the mask labels as their rtstruct names

        if nnunet_info:
            if label_or_image == "labels":
                filename = f"{subject_id}.nii.gz"  # naming convention for labels
            else:
                filename = self.filename_format.format(
                    subject_id=subject_id,
                    modality_index=nnunet_info["modalities"][
                        nnunet_info["current_modality"]
                    ],
                )  # naming convention for images
            out_path = self._get_path_from_subject_id(
                filename, label_or_image=label_or_image, train_or_test=train_or_test
            )
        else:
            out_path = self._get_path_from_subject_id(
                self.filename_format, subject_id=subject_id
            )
        sitk.WriteImage(image, out_path, self.compress)

    def _get_path_from_subject_id(self, filename, **kwargs):
        root_directory = self.root_directory.format(
            **kwargs
        )  # replace the {} with the kwargs passed in from .put() (above)
        out_path = Path(root_directory, filename).as_posix()
        out_dir = os.path.dirname(out_path)
        if self.create_dirs and not os.path.exists(out_dir):
            os.makedirs(
                out_dir, exist_ok=True
            )  # create subdirectories if specified in filename_format
        return out_path

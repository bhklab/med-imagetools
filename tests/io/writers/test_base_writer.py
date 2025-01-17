from pathlib import Path

import pytest

from imgtools.exceptions import DirectoryNotFoundError
from imgtools.io.writers import AbstractBaseWriter, ExistingFileMode


class SimpleWriter(AbstractBaseWriter):
    def save(self, content: str) -> Path:
        file_path = self.resolve_path()
        with open(file_path, "w") as f:
            f.write(content)
        return file_path


class MediumWriter(AbstractBaseWriter):
    def save(self, content: str, suffix: str = "") -> Path:
        file_path = self.resolve_path(suffix=suffix)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path


class ComplexWriter(AbstractBaseWriter):
    def save(self, content: str, metadata: dict) -> Path:
        file_path = self.resolve_path(**metadata)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path


def test_simple_writer(tmp_path):
    writer = SimpleWriter(root_directory=tmp_path, filename_format="{date_time}.txt")
    with writer:
        file_path = writer.save("Simple content")
    assert file_path.exists()
    assert file_path.read_text() == "Simple content"


def test_medium_writer(tmp_path):
    writer = MediumWriter(
        root_directory=tmp_path, filename_format="{date_time}_{suffix}.txt"
    )
    with writer:
        file_path = writer.save("Medium content", suffix="test")
    assert file_path.exists()
    assert file_path.read_text() == "Medium content"


def test_complex_writer(tmp_path):
    writer = ComplexWriter(
        root_directory=tmp_path, filename_format="{date_time}_{user}.txt"
    )
    with writer:
        file_path = writer.save("Complex content", metadata={"user": "testuser"})
    assert file_path.exists()
    assert file_path.read_text() == "Complex content"


def test_context_manager_cleanup(tmp_path):
    subdir = tmp_path / "nested"
    writer = SimpleWriter(root_directory=subdir, filename_format="{date_time}.txt")
    with writer:
        assert subdir.exists()
    assert not subdir.exists()


def test_directory_creation(tmp_path):
    writer = SimpleWriter(
        root_directory=tmp_path / "nested", filename_format="{date_time}.txt"
    )
    with writer:
        file_path = writer.save("Content")
    assert file_path.exists()
    assert file_path.read_text() == "Content"
    assert (tmp_path / "nested").exists()


def test_directory_not_created_if_exists(tmp_path):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    writer = SimpleWriter(
        root_directory=existing_dir, filename_format="{date_time}.txt"
    )
    with writer:
        file_path = writer.save("Content")
    assert file_path.exists()
    assert file_path.read_text() == "Content"
    assert existing_dir.exists()


def test_writer_put_exit(tmp_path):
    writer = SimpleWriter(root_directory=tmp_path, filename_format="{date_time}.txt")
    with pytest.raises(SystemExit) as excinfo:
        writer.put()
    assert excinfo.value.code == 1


def test_no_create_dirs_non_existent(tmp_path):
    with pytest.raises(DirectoryNotFoundError):
        with SimpleWriter(
            root_directory=tmp_path / "nested_non_existent",
            filename_format="{date_time}.txt",
            create_dirs=False,
        ) as writer:
            file_path = writer.save("Content")  # noqa


def test_pre_check_context(tmp_path):
    writer = SimpleWriter(
        root_directory=tmp_path,
        filename_format="{subject}_{name}.txt",
        existing_file_mode=ExistingFileMode.FAIL,
    )
    if path := writer.preview_path(subject="math", name="context_test"):
        file_path = writer.save("Content")
        assert file_path.exists()
        assert file_path == path
        assert writer.context["name"] == "context_test"

    # assert writer.context == {}

    with pytest.raises(FileExistsError):
        if writer.preview_path(subject="math", name="context_test"):
            pass

    with pytest.raises(FileExistsError):
        another_path = writer.preview_path(subject="math", name="context_test")  # noqa

    successfulpath = writer.preview_path(subject="math", name="context_test2")
    assert not successfulpath.exists()

    skip_writer = SimpleWriter(
        root_directory=tmp_path,
        filename_format="{subject}_{name}.txt",
        existing_file_mode=ExistingFileMode.SKIP,
    )

    assert skip_writer.preview_path(subject="math", name="context_test") is None

    overwrite_writer = SimpleWriter(
        root_directory=tmp_path,
        filename_format="{subject}_{name}.txt",
        existing_file_mode=ExistingFileMode.OVERWRITE,
    )

    assert (
        overwrite_writer.preview_path(subject="math", name="context_test") is not None
    )

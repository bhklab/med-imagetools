from dataclasses import asdict, dataclass, fields
from typing import Any, Iterator, List, Sequence


@dataclass
class DataclassMixin:
    """Mixin class to provide common methods for dataclasses."""

    def keys(self) -> List[str]:
        return [attr_field.name for attr_field in fields(self)]

    def items(self) -> List[tuple[str, Any]]:
        return [
            (attr_field.name, getattr(self, attr_field.name))
            for attr_field in fields(self)
        ]

    def to_dict(self) -> dict:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:  # noqa
        return getattr(self, key)

    def __rich_repr__(self) -> Iterator[tuple[str, str | Sequence[str]]]:
        # for each key-value pair, 'yield key, value'
        for attr_field in fields(self):
            if attr_field.name.endswith("UID"):
                yield (
                    attr_field.name,
                    f"...{getattr(self, attr_field.name)[-10:]}",
                )
            else:
                yield attr_field.name, getattr(self, attr_field.name)

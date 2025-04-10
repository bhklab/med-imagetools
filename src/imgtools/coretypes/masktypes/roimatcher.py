from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator

PatternString = str
ROI_MatchingType = dict[str, list[PatternString]]

InputType = Annotated[
    ROI_MatchingType
    | dict[str, PatternString]
    | list[PatternString]
    | PatternString
    | None,
    Field(description="Flexible input for ROI matcher"),
]


class ROIMatcher(BaseModel):
    roi_map: InputType
    default_key: ClassVar[str] = Field(default="ROI")

    @field_validator("roi_map")
    @classmethod
    def validate_roi_map(cls, v: InputType) -> ROI_MatchingType:
        match v:
            case dict():
                if not v:
                    return {cls.default_key: [".*"]}
                cleaned = {}
                for k, val in v.items():
                    if isinstance(val, str):
                        cleaned[k] = [val]
                    elif isinstance(val, list):
                        cleaned[k] = val
                    else:
                        msg = f"Invalid type for key '{k}': {type(val)}"
                        raise TypeError(msg)
                return cleaned
            case list():
                return {cls.default_key: v}
            case str():
                return {cls.default_key: [v]}
            case None:
                return {cls.default_key: [".*"]}
            case _:  # pragma: no cover
                msg = f"Unrecognized ROI matching input type: {type(v)}"
                raise TypeError(msg)


from rich import print

r1 = ROIMatcher(roi_map={"ROI": [".*"]})
print(r1)

r2 = ROIMatcher(roi_map={"ROI": "GTV"})
print(r2)

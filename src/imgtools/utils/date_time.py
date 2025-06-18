from datetime import date, datetime, time
from typing import Tuple, Union


# Given a dictionary with all sorts of key values,
# go through all the keys, and if the key is a date or time,
# parse it into a datetime object.
def convert_dictionary_datetime_values(
    dicom_dict: dict[str, str],
) -> dict[str, date | time | float | str]:
    """
    Convert date/time/duration strings in a DICOM metadata dictionary.

    This function iterates over all key-value pairs in a dictionary and attempts
    to convert strings that appear to represent date, time, or duration fields into
    corresponding Python types (`date`, `time`, or `float`). Keys that do not match
    temporal patterns are returned unchanged with their original string values.

    Parameters
    ----------
    dicom_dict : dict[str, str]
            A dictionary containing DICOM metadata with string values.

    Returns
    -------
    dict[str, date | time | float | str]
            A new dictionary where values for date/time/duration fields are parsed
            into native Python types when possible. All keys are retained.

    Examples
    --------
    >>> dicom_dict = {
    ...     "AcquisitionDate": "20240101",
    ...     "EchoTime": "45.0",
    ...     "InstanceNumber": "5",
    ... }
    >>> convert_dictionary_datetime_values(dicom_dict)
    {
        'AcquisitionDate': datetime.date(2024, 1, 1),
        'EchoTime': 45.0,
        'InstanceNumber': '5'
    }
    """
    result: dict[str, date | time | float | str] = {}

    for key, value in dicom_dict.items():
        if not isinstance(value, str):
            # Skip non-string values
            result[key] = value
            continue
        if value and value.lower() != "none":
            key_lower = key.lower()
            if (
                "date" in key_lower
                or "time" in key_lower
                or "duration" in key_lower
            ):
                try:
                    result[key] = parse_datetime(key, value)
                    continue
                except Exception:
                    pass  # fall through to keep raw value

        result[key] = value

    return result


# duration fields → parse as float
def parse_datetime(key: str, value: str) -> date | time | float:
    """
    Parse date/time or duration values from keyword/value pairs.

    Parameters
    ----------
    key : str
        The name of the DICOM field (e.g., "AcquisitionTime", "EchoTime").
    value : str
        The associated value to be parsed.

    Returns
    -------
    date or time or float
        Depending on the field type, returns either a Python date, time,
        or a float representing a duration.

    Raises
    ------
    ValueError
        If the value cannot be parsed correctly for the given field type.
    TypeError
        If the parsed result is not a date or time object, when such an
        object is expected.

    Examples
    --------
    >>> parse_datetime("EchoTime", "45.0")
    45.0
    >>> parse_datetime("AcquisitionDate", "20240101")
    datetime.date(2024, 1, 1)
    >>> parse_datetime("AcquisitionTime", "230000")
    datetime.time(23, 0)
    """
    # duration fields → parse as float
    DURATION_FIELDS = {  # noqa: N806
        "EchoTime",
        "RepetitionTime",
        "InversionTime",
        "FrameReferenceTime",
        "FrameTime",
        "AcquisitionDuration",
        "ExposureTime",
    }

    # clock-style time fields → parse as HHMMSS
    CLOCK_FIELDS = {  # noqa: N806
        "AcquisitionTime",
        "ContentTime",
        "InstanceCreationTime",
        "SeriesTime",
        "StudyTime",
        "StructureSetTime",
    }

    if not value or value.lower() == "none":
        # msg = f"Empty or 'None' value for key: {key}"
        # return 0 as default for empty values
        return 0
    key_base = str(key)

    # Check if this is a duration field first (highest priority)
    if key_base in DURATION_FIELDS:
        try:
            # should return datetime.time as a duration
            return float(value)
        except ValueError as e:
            msg = f"Failed to parse duration field {key}='{value}' as float"
            raise ValueError(msg) from e

    # Next, check if this is a clock-style time field
    if key_base in CLOCK_FIELDS:
        ok, result = parse_dicom_time(value)
    elif "Date" in key_base:
        ok, result = parse_dicom_date(value)
    elif "Time" in key_base:
        ok, result = parse_dicom_time(value)
    else:
        # For unknown keys, try datetime parsing as fallback
        try:
            assert value.isdigit(), (
                f"Non-digit characters in date/time: {value}"
            )
            ok, result = parse_dicom_date(value)
        except (ValueError, AssertionError) as e:
            msg = f"Unknown DICOM key: '{key}'"
            raise ValueError(msg) from e

    if not ok:
        msg = f"Failed to parse {key}='{value}': {result}"
        raise ValueError(msg)

    if not isinstance(result, (date, time)):
        msg = f"Expected date or time object, got {type(result)}"
        raise TypeError(msg)

    return result


ParsedResult = Tuple[bool, Union[date, time, datetime, str]]


def parse_dicom_date(dicom_date: str) -> ParsedResult:
    if len(dicom_date) != 8:
        return (
            False,
            f"Expected 8-digit date string, got {len(dicom_date)} characters",
        )

    if not dicom_date.isdigit():
        return False, f"Non-digit characters in date: {dicom_date}"

    try:
        return True, datetime.strptime(dicom_date, "%Y%m%d").date()
    except ValueError as e:
        return False, f"Failed to parse date '{dicom_date}': {e}"


def parse_dicom_time(dicom_time: str) -> ParsedResult:
    if not any(c.isdigit() for c in dicom_time):
        return False, f"No digits found in time: {dicom_time}"

    # Try standard formats
    try:
        return True, datetime.strptime(dicom_time, "%H%M%S.%f").time()
    except ValueError:
        return True, datetime.strptime(dicom_time, "%H%M%S").time()


def datetime_to_iso_string(
    datetime_obj: datetime | date | time,
) -> str:
    """Convert datetime/date/time to an ISO 8601 string with second precision.

    Parameters
    ----------
    datetime_obj : datetime.datetime or datetime.date or datetime.time
        The datetime, date, or time object to convert.

    Returns
    -------
    str
        Formatted ISO 8601 string.

    Raises
    ------
    TypeError
        If 'datetime_obj' is not a datetime, date, or time object.

    Examples
    --------
    >>> datetime_to_iso_string(
    ...     datetime.datetime(2024, 1, 1, 12, 0, 0)
    ... )
    '2024-01-01T12:00:00'
    >>> datetime_to_iso_string(datetime.date(2024, 1, 1))
    '2024-01-01'
    >>> datetime_to_iso_string(datetime.time(12, 0, 0))
    '12:00:00'
    """
    if isinstance(datetime_obj, datetime):
        return datetime_obj.isoformat(timespec="seconds")
    if isinstance(datetime_obj, date):
        return datetime_obj.isoformat()
    if isinstance(datetime_obj, time):
        return datetime_obj.isoformat(timespec="seconds")
    raise TypeError("Expected a datetime, date, or time object.")


# if __name__ == "__main__":  # pragma: no cover
#     import json
#     from pathlib import Path

#     from rich import print

#     def test_dicom_parsing(dates_path: Path, times_path: Path) -> None:
#         with open(dates_path) as f:
#             date_data = json.load(f)
#         with open(times_path) as f:
#             time_data = json.load(f)

#         failures = []
#         count = 0
#         success_dict = {}
#         for i, (dataset, name) in enumerate(
#             [(date_data, "dates"), (time_data, "times")]
#         ):
#             for patient_id, series in dataset.items():
#                 for instance_id, fields in series.items():
#                     for key, val in fields.items():
#                         if not val:
#                             continue
#                         try:
#                             result = parse_datetime(key, val)
#                         except Exception as e:
#                             failures.append(
#                                 (
#                                     f"{name}:{patient_id}/{instance_id}",
#                                     key,
#                                     val,
#                                     str(e),
#                                 )
#                             )
#                         if f"{key}:{val}" not in success_dict:
#                             success_dict[f"{key}:{val}"] = set()
#                             print(
#                                 f"Original key: {key}\nOriginal value: {val}\nParsed value: {result}\n\n"
#                             )

#                     count += 1
#             count = 0

#         if failures:
#             print(f"❌ Found {len(failures)} parsing issues:\n")
#             for ref, key, val, err in failures:
#                 print(f"{ref} | {key}='{val}' → {err}")
#         else:
#             print("✅ All date/time fields parsed successfully.")

#     test_dicom_parsing(Path("dates.json"), Path("times.json"))
#     print("✅ All DICOM date/time values parsed successfully.")

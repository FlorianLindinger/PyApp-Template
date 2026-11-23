"""python_version requests that allow more than one minor version: "3", ">=3.12", "3.12-3.14".

Such a loose request could resolve to another minor version whenever uv offers a newer Python, which
would leave the project's lock file (requires-python "==X.Y.*") unusable. So the project records the
version it actually got in pyapp/generated/.python-version, as it does for "" (newest stable, chosen
once), and the setting counts as unchanged as long as that recorded version is inside it.

Only plain CPython version numbers are understood here; any other request ("pypy@3.11", "3.14t") is
passed to uv unchanged and recorded as it is. scripts/bootstrap/resolve_runtime.py repeats range_specifier()
because it cannot import the launcher; tests/src/test_resolve_runtime.py compares the two.

Standalone: copy this file anywhere (standard library only); useful wherever Python version
requests are handed to uv.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# (operator, version numbers, ends in ".*")
Clause = Tuple[str, Tuple[int, ...], bool]

_NUMBERS = r"\d+(?:\.\d+){0,2}"
_RANGE = re.compile(r"\s*(" + _NUMBERS + r")\s*-\s*(" + _NUMBERS + r")\s*")
_CLAUSE = re.compile(r"\s*(>=|<=|==|!=|~=|>|<)\s*(\d+(?:\.\d+)*)(\.\*)?\s*")
_MAJOR_ONLY = re.compile(r"\s*(\d+)\s*")
_RECORDED = re.compile(r"\s*(\d+)\.(\d+)(?:\.(\d+))?\s*")
# Patch numbers that stand for "every patch release of a minor version" (see _whole_minor).
_SAMPLE_PATCHES = (0, 1, 999)


def _numbers(text: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _text(numbers: Tuple[int, ...]) -> str:
    return ".".join(str(part) for part in numbers)


def _padded(numbers: Tuple[int, ...]) -> Tuple[int, ...]:
    """3.12 and 3.12.0 compare equal, as in PEP 440."""
    return numbers + (0,) * (3 - len(numbers))


def range_ends(value: str) -> Optional[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """The lower and upper end of a range such as "3.12-3.14" (either order), or None."""
    match = _RANGE.fullmatch(value)
    if not match:
        return None
    low, high = _numbers(match.group(1)), _numbers(match.group(2))
    return (high, low) if _padded(high) < _padded(low) else (low, high)


def range_specifier(value: str) -> Optional[str]:
    """ ">=3.12,<3.15" for "3.12-3.14" or "3.14-3.12"; None if value is not a range.

    uv has no range syntax, so a range becomes a version specifier. Its upper end includes all its
    releases: "3.14" every 3.14.x, "3.14.2" up to 3.14.2 (PEP 440's "<=3.14" would stop at 3.14.0).
    """
    ends = range_ends(value)
    if ends is None:
        return None
    low, high = ends
    upper = "<=" + _text(high) if len(high) == 3 else "<" + _text((*high[:-1], high[-1] + 1))
    return f">={_text(low)},{upper}"


def uv_request(value: str) -> str:
    """The python_version text as uv understands it (only ranges need converting)."""
    return range_specifier(value) or value


def loose_clauses(value: str) -> Optional[List[Clause]]:
    """The version clauses of a loose numeric request, or None for any other request."""
    text = range_specifier(value) or value
    major = _MAJOR_ONLY.fullmatch(text)
    if major:
        return [("==", (int(major.group(1)),), True)]
    clauses: List[Clause] = []
    for part in text.split(","):
        match = _CLAUSE.fullmatch(part)
        if not match or (match.group(3) and match.group(1) not in ("==", "!=")):
            return None
        clauses.append((match.group(1), _numbers(match.group(2)), bool(match.group(3))))
    return clauses


def _satisfies(version: Tuple[int, ...], clauses: List[Clause]) -> bool:
    actual = _padded(version[:3])
    for operator, numbers, wildcard in clauses:
        if wildcard:
            same = actual[: len(numbers)] == numbers
            ok = same if operator == "==" else not same
        elif operator == "~=":
            prefix = numbers[:-1]
            ok = actual >= _padded(numbers) and actual[: len(prefix)] == prefix
        else:
            wanted = _padded(numbers)
            ok = {
                ">=": actual >= wanted,
                "<=": actual <= wanted,
                ">": actual > wanted,
                "<": actual < wanted,
                "!=": actual != wanted,
                "==": actual == wanted,
            }[operator]
        if not ok:
            return False
    return True


def _whole_minor(minor: Tuple[int, ...], clauses: List[Clause]) -> bool:
    """Every patch release of minor satisfies the clauses, so recording just "X.Y" is safe.

    A clause naming a patch inside this minor ("<=3.14.2", "!=3.14.1") cuts it; so do ">3.14",
    "<=3.14" and "==3.14", which PEP 440 reads as 3.14.0 and which the sample patches catch.
    """
    if any(len(numbers) >= 3 and not wildcard and numbers[:2] == minor for _, numbers, wildcard in clauses):
        return False
    return all(_satisfies((*minor[:2], patch), clauses) for patch in _SAMPLE_PATCHES)


def allows(value: str, version: Tuple[int, ...]) -> bool:
    """A loose request accepts this Python version (False for other kinds of request)."""
    clauses = loose_clauses(value)
    return clauses is not None and _satisfies(version, clauses)


def recorded_request(value: str, version: Tuple[int, ...]) -> str:
    """What .python-version records for the setting value once Python version is in use.

    "" and loose requests record "X.Y", or "X.Y.Z" when the request does not allow every patch of
    that minor; every other request is recorded as it is, as before.
    """
    minor = version[:2]
    if value:
        clauses = loose_clauses(value)
        if clauses is None:
            return value
        if not _whole_minor(minor, clauses):
            return _text(version[:3])
    return _text(minor)


def request_matches(setting_value: str, file_value: Optional[str]) -> bool:
    """The setting still describes the Python recorded in .python-version.

    "" accepts any recorded Python; a loose request accepts a recorded "X.Y" whose patches it all
    allows, or a recorded "X.Y.Z" it allows; otherwise both texts must be equal.
    """
    if file_value is None:
        return False
    if not setting_value or setting_value.strip().lower() == file_value.strip().lower():
        return True
    clauses = loose_clauses(setting_value)
    recorded = _RECORDED.fullmatch(file_value)
    if clauses is None or not recorded:
        return False
    if recorded.group(3) is None:
        return _whole_minor((int(recorded.group(1)), int(recorded.group(2))), clauses)
    return _satisfies(tuple(int(part) for part in recorded.groups()), clauses)

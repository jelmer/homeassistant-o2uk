"""Parse the My O2 (UK) ecare dashboard HTML.

The dashboard at ``https://www.o2.co.uk/ecare/home`` is a Next.js
server-rendered page. The data we want is embedded inline as React
Server Components (RSC) Flight chunks: a series of
``self.__next_f.push([1, "<chunk>"])`` calls whose chunks concatenate
into a stream of JSON-typed lines.

We don't try to be a Flight client; we just concatenate the chunks and
hunt for the small number of JSON objects that carry usage data and the
product (SIM) record.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

_PUSH_RE = re.compile(
    r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)',
)


@dataclass
class O2Allowance:
    """A single allowance (group) reported by the dashboard."""

    name: str  # "Data" / "Minutes" / "Text messages"
    initial: float | None
    used: float | None
    remaining: float | None
    unit: str | None
    unlimited: bool


@dataclass
class O2Snapshot:
    """Structured snapshot extracted from the ecare dashboard HTML."""

    msisdn: str | None
    product_type: str | None
    tariff_monthly_charge: float | None
    spend_cap: float | None
    allowances: dict[str, O2Allowance]  # keyed by group ("data" / "voice" / "sms")
    reset_date: datetime | None


def parse_dashboard_html(html: str) -> O2Snapshot:
    """Extract a snapshot from the ecare home dashboard HTML."""
    rsc = _join_rsc_chunks(html)
    allowances_raw = _find_allowances(rsc)
    product = _find_product(rsc)
    spend_cap = _find_spend_cap(rsc)
    reset = _find_reset_date(html)

    return O2Snapshot(
        msisdn=product.get("number") if product else None,
        product_type=product.get("productType") if product else None,
        tariff_monthly_charge=_to_float(product.get("mrcWithTax")) if product else None,
        spend_cap=spend_cap,
        allowances=_normalize_allowances(allowances_raw),
        reset_date=reset,
    )


def _join_rsc_chunks(html: str) -> str:
    """Concatenate all ``self.__next_f.push`` payload chunks."""
    parts: list[str] = []
    for match in _PUSH_RE.finditer(html):
        # Each chunk is a JSON-encoded string literal; decode the escapes
        # by parsing it as a JSON string.
        try:
            parts.append(json.loads(f'"{match.group(1)}"'))
        except json.JSONDecodeError:
            _LOGGER.debug("Skipping malformed RSC chunk")
    return "".join(parts)


def _find_allowances(rsc: str) -> list[dict[str, Any]]:
    """Locate the ``"allowances":[...]`` array and parse it."""
    key = '"allowances":'
    idx = rsc.find(key)
    while idx != -1:
        start = rsc.find("[", idx + len(key))
        if start == -1:
            break
        end = _match_bracket(rsc, start, "[", "]")
        if end is None:
            break
        try:
            value = json.loads(rsc[start : end + 1])
        except json.JSONDecodeError:
            idx = rsc.find(key, end)
            continue
        if isinstance(value, list) and value and "groupName" in value[0]:
            return value
        idx = rsc.find(key, end)
    return []


def _find_product(rsc: str) -> dict[str, Any] | None:
    """Locate the SIM/product object containing ``"number":"07..."``.

    The product record has shape ``{"id":"...","number":"07...",...,
    "productType":"paym",...}``. We do a single forward pass through
    ``rsc`` tracking string state and ``{}`` depth; for each ``"productType"``
    match we report the innermost open object that contains it.
    """
    targets = [m.start() for m in re.finditer(r'"productType":"(?:paym|payg)"', rsc)]
    if not targets:
        return None
    target_set = set(targets)

    stack: list[int] = []
    in_string = False
    escape = False
    candidates: list[tuple[int, int]] = []  # (opener, closer)

    for i, c in enumerate(rsc):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            stack.append(i)
        elif c == "}":
            if not stack:
                continue
            opener = stack.pop()
            # If any productType target lies inside this object, capture it.
            for t in target_set:
                if opener < t < i:
                    candidates.append((opener, i))
                    break

    for opener, closer in candidates:
        try:
            obj = json.loads(rsc[opener : closer + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("number"):
            return obj
    return None


def _find_spend_cap(rsc: str) -> float | None:
    """Find a Spend Cap entry's ``"subtitle":"£XX.YY"`` value."""
    pattern = re.compile(r'"title":"Spend Cap"[^{}]*?"subtitle":"£([\d.]+)"', re.DOTALL)
    match = pattern.search(rsc)
    if match:
        return _to_float(match.group(1))
    return None


def _find_reset_date(html: str) -> datetime | None:
    """Parse the visible "Resets on DD Mon" text on the dashboard."""
    match = re.search(r"Resets on (\d{1,2})\s+([A-Za-z]+)", html)
    if not match:
        return None
    day = int(match.group(1))
    month_name = match.group(2)
    today = datetime.now(UTC).replace(tzinfo=None)
    for year in (today.year, today.year + 1):
        try:
            candidate = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
        except ValueError:
            try:
                candidate = datetime.strptime(f"{day} {month_name} {year}", "%d %b %Y")
            except ValueError:
                return None
        if candidate >= today.replace(hour=0, minute=0, second=0, microsecond=0):
            return candidate
    return None


def _match_bracket(text: str, start: int, opener: str, closer: str) -> int | None:
    """Return the index of the matching closer for the bracket at ``start``."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
    return None


# Mapping from the dashboard's groupName / type to our canonical keys.
_GROUP_KEYS = {
    "data": "data",
    "minutes": "voice",
    "text messages": "sms",
    "messages": "sms",
}


def _normalize_allowances(raw: list[dict[str, Any]]) -> dict[str, O2Allowance]:
    """Translate the raw ``allowances`` array into our typed map."""
    result: dict[str, O2Allowance] = {}
    for entry in raw:
        name = entry.get("groupName", "")
        key = _GROUP_KEYS.get(name.lower())
        if key is None:
            continue

        initial_str = entry.get("initialAllowance")
        used_str = entry.get("allowanceUsed")
        remaining_str = entry.get("allowanceRemaining")

        initial, _ = _parse_amount(initial_str)
        used, used_unit = _parse_amount(used_str)
        remaining, rem_unit = _parse_amount(remaining_str)

        unit = rem_unit or used_unit
        unlimited = initial is None or initial < 0

        # Compute remaining if not provided but initial+used are
        if remaining is None and initial is not None and used is not None and not unlimited:
            remaining = max(initial - used, 0.0)

        result[key] = O2Allowance(
            name=name,
            initial=None if unlimited else initial,
            used=used,
            remaining=remaining,
            unit=unit,
            unlimited=unlimited,
        )
    return result


_AMOUNT_RE = re.compile(r"^\s*(-?[\d.]+)\s*([A-Za-z]+)?\s*$")


def _parse_amount(value: Any) -> tuple[float | None, str | None]:
    """Parse strings like ``"5.04 GB"`` / ``"22 mins"`` / ``"6"`` / ``"-1"``.

    Returns (value, unit). Data values are normalised to GB (1024 MB).
    """
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None
    s = str(value).strip()
    m = _AMOUNT_RE.match(s)
    if not m:
        return None, None
    try:
        n = float(m.group(1))
    except ValueError:
        return None, None
    unit = (m.group(2) or "").strip()

    # Normalize data sizes to GB
    if unit.upper() == "MB":
        return n / 1024.0, "GB"
    if unit.upper() == "KB":
        return n / (1024.0 * 1024.0), "GB"
    if unit.upper() == "GB":
        return n, "GB"
    return n, unit or None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

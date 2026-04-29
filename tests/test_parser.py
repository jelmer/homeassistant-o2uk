"""Tests for the ecare-dashboard HTML parser."""

from __future__ import annotations

import gzip
import os

from custom_components.o2uk.parser import (
    O2Allowance,
    O2Snapshot,
    parse_dashboard_html,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ecare_home.html.gz")


def _load_fixture() -> str:
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as f:
        return f.read()


def test_parse_real_dashboard_html() -> None:
    html = _load_fixture()
    snap = parse_dashboard_html(html)

    assert isinstance(snap, O2Snapshot)
    assert snap.msisdn == "07700900000"
    assert snap.product_type == "paym"
    assert snap.tariff_monthly_charge == 14.5
    assert snap.spend_cap == 30.0

    data = snap.allowances["data"]
    assert isinstance(data, O2Allowance)
    assert data.unlimited is False
    assert data.initial == 100.0
    assert data.used == 5.04
    assert data.remaining == 94.96
    assert data.unit == "GB"

    voice = snap.allowances["voice"]
    assert voice.unlimited is True
    assert voice.used == 22.0  # "22 mins"
    assert voice.unit == "mins"

    sms = snap.allowances["sms"]
    assert sms.unlimited is True
    assert sms.used == 6.0


def test_parse_handles_empty_html() -> None:
    snap = parse_dashboard_html("<html></html>")
    assert snap.msisdn is None
    assert snap.tariff_monthly_charge is None
    assert snap.allowances == {}


def test_parse_handles_garbage() -> None:
    # Half-formed RSC chunk should not raise
    snap = parse_dashboard_html('<script>self.__next_f.push([1, "not valid json"])</script>')
    assert snap.msisdn is None
    assert snap.allowances == {}

"""Tests for the parsing logic in coordinator._parse."""

from __future__ import annotations

from datetime import datetime

from custom_components.o2uk.coordinator import _parse

SAMPLE_ALLOWANCES = {
    "tariffVM": {
        "number": "447700900123",
        "name": "O2 Refresh – Custom Plan",
        "subcategory": "Pay Monthly",
    },
    "allowancesBalance": {
        "data": [
            {
                "balance": 5120,  # MB remaining
                "initialBalance": 20480,
                "unit": "MB",
                "details": [{"expiresDate": "15 May 2026"}],
            }
        ],
        "voice": [
            {
                "balance": 750,
                "initialBalance": 1000,
                "unit": "min",
                "details": [],
            }
        ],
        "text": [
            {
                "balance": 4900,
                "initialBalance": 5000,
                "unit": "messages",
                "details": [],
            }
        ],
    },
}


def test_parse_basic_allowances() -> None:
    data = _parse(SAMPLE_ALLOWANCES, None)

    assert data.msisdn == "447700900123"
    assert data.plan_name == "O2 Refresh – Custom Plan"
    assert data.plan_subcategory == "Pay Monthly"

    assert data.data is not None
    assert data.data.balance == 5120.0
    assert data.data.initial == 20480.0
    assert data.data.unit == "MB"
    assert data.data.expires == datetime(2026, 5, 15)

    assert data.voice is not None
    assert data.voice.balance == 750.0
    assert data.voice.initial == 1000.0

    assert data.text is not None
    assert data.text.balance == 4900.0

    assert data.latest_bill_amount is None
    assert data.latest_bill_date is None


def test_parse_unlimited_data() -> None:
    payload = {
        "tariffVM": {"number": "447700900123"},
        "allowancesBalance": {
            "data": [{"unit": "MB"}],  # no balance => unlimited
            "voice": [],
            "text": [],
        },
    }
    data = _parse(payload, None)
    assert data.data is not None
    assert data.data.balance is None
    assert data.voice is None
    assert data.text is None


def test_parse_bad_expires_date_is_tolerated() -> None:
    payload = {
        "tariffVM": {"number": "447700900123"},
        "allowancesBalance": {
            "data": [
                {
                    "balance": 1024,
                    "initialBalance": 2048,
                    "unit": "MB",
                    "details": [{"expiresDate": "not-a-date"}],
                }
            ]
        },
    }
    data = _parse(payload, None)
    assert data.data is not None
    assert data.data.expires is None


def test_parse_bills() -> None:
    bills = {
        "bills": [
            {
                "amount": "29.50",
                "billDate": "01 April 2026",
                "currency": "GBP",
            },
            {
                "amount": "29.50",
                "billDate": "01 March 2026",
                "currency": "GBP",
            },
        ]
    }
    data = _parse(SAMPLE_ALLOWANCES, bills)
    assert data.latest_bill_amount == 29.5
    assert data.latest_bill_date == datetime(2026, 4, 1)
    assert data.latest_bill_currency == "GBP"


def test_parse_bills_alternate_keys() -> None:
    bills = {
        "billList": [
            {"totalAmount": 12.34, "issueDate": "2026-04-01"},
        ]
    }
    data = _parse(SAMPLE_ALLOWANCES, bills)
    assert data.latest_bill_amount == 12.34
    assert data.latest_bill_date == datetime(2026, 4, 1)
    # currency defaults to GBP if absent
    assert data.latest_bill_currency == "GBP"


def test_parse_no_bills_payload() -> None:
    data = _parse(SAMPLE_ALLOWANCES, {"bills": []})
    assert data.latest_bill_amount is None
    assert data.latest_bill_date is None
    assert data.latest_bill_currency is None

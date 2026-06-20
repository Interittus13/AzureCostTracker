import pytest
from decimal import Decimal
from src.utils.utils import calculate_cost, get_cost_breakdown, format_currency

def test_calculate_cost():
    # Test typical decimal summation
    mock_data = {
        "properties": {
            "rows": [
                [10.5, "2026-06-18", "Virtual Machines", "CAD"],
                [20.3, "2026-06-18", "Storage Accounts", "CAD"]
            ]
        }
    }
    assert calculate_cost(mock_data) == Decimal("30.80")

    # Test handling of empty rows
    assert calculate_cost({}) == Decimal("0.00")

def test_get_cost_breakdown():
    mock_data = {
        "properties": {
            "rows": [
                [30.5, "2026-06-18", "Virtual Machines", "CAD"],
                [10.2, "2026-06-18", "Storage Accounts", "CAD"]
            ]
        }
    }
    breakdown, total = get_cost_breakdown(mock_data)
    assert len(breakdown) == 2
    assert breakdown[0]["service"] == "Virtual Machines"
    assert breakdown[0]["cost"] == "$30.50"
    assert breakdown[0]["raw_cost"] == 30.5
    assert breakdown[1]["service"] == "Storage Accounts"
    assert breakdown[1]["cost"] == "$10.20"
    assert breakdown[1]["raw_cost"] == 10.2
    assert total == "$40.70"

def test_format_currency():
    assert format_currency(1234.567) == "$1,234.57"
    assert format_currency(1234.567, "€") == "€1,234.57"
    assert format_currency("not-a-number") == "not-a-number"

def test_get_cost_breakdown_eur():
    mock_data = {
        "properties": {
            "rows": [
                [30.5, "2026-06-18", "Virtual Machines", "EUR"]
            ]
        }
    }
    breakdown, total = get_cost_breakdown(mock_data)
    assert breakdown[0]["cost"] == "€30.50"
    assert total == "€30.50"

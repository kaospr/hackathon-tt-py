"""
Integration tests for GET /api/v1/portfolio/dividends.

Tests the dividends endpoint which returns dividend activities grouped by date.
Only DIVIDEND-type activities appear in the response; BUY/SELL are excluded.

Scenarios:
  - Empty portfolio (no dividends)
  - Single dividend (MSFT buy + dividend)
  - Multiple dividends on separate dates
  - GroupBy month/year aggregation
  - BUY-only portfolio returns no dividends

Derived from portfolio-calculator-msft-buy-with-dividend.spec.ts
"""
import pytest

from .mock_prices import prices_for


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def msft_with_dividend(gf):
    """
    MSFT buy + dividend (open position):
      BUY 1 MSFT @ USD 298.58, fee 19 — 2021-09-16
      DIVIDEND 1 MSFT @ USD 0.62, fee 0 — 2021-11-16
    """
    client, _ = gf
    client.update_user_settings("USD")
    client.import_activities([
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2021-09-16",
            "fee": 19,
            "quantity": 1,
            "symbol": "MSFT",
            "type": "BUY",
            "unitPrice": 298.58,
        },
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2021-11-16",
            "fee": 0,
            "quantity": 1,
            "symbol": "MSFT",
            "type": "DIVIDEND",
            "unitPrice": 0.62,
        },
    ])
    client.seed_market_data("YAHOO", "MSFT", prices_for("MSFT"))
    return client


@pytest.fixture
def msft_multiple_dividends(gf):
    """
    MSFT buy + two dividends on different dates:
      BUY 1 MSFT @ USD 298.58, fee 19 — 2021-09-16
      DIVIDEND 1 MSFT @ USD 0.62, fee 0 — 2021-11-16
      DIVIDEND 1 MSFT @ USD 0.62, fee 0 — 2023-07-10
    """
    client, _ = gf
    client.update_user_settings("USD")
    client.import_activities([
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2021-09-16",
            "fee": 19,
            "quantity": 1,
            "symbol": "MSFT",
            "type": "BUY",
            "unitPrice": 298.58,
        },
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2021-11-16",
            "fee": 0,
            "quantity": 1,
            "symbol": "MSFT",
            "type": "DIVIDEND",
            "unitPrice": 0.62,
        },
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2023-07-10",
            "fee": 0,
            "quantity": 1,
            "symbol": "MSFT",
            "type": "DIVIDEND",
            "unitPrice": 0.62,
        },
    ])
    client.seed_market_data("YAHOO", "MSFT", prices_for("MSFT"))
    return client


@pytest.fixture
def btcusd_buy_only(gf):
    """BUY 1 BTCUSD — no dividends."""
    client, _ = gf
    client.update_user_settings("USD")
    client.import_activities([
        {
            "currency": "USD",
            "dataSource": "YAHOO",
            "date": "2021-12-12",
            "fee": 4.46,
            "quantity": 1,
            "symbol": "BTCUSD",
            "type": "BUY",
            "unitPrice": 44558.42,
        },
    ])
    client.seed_market_data("YAHOO", "BTCUSD", prices_for("BTCUSD"))
    return client


# ===========================================================================
# Empty portfolio
# ===========================================================================

def test_no_orders_dividends_are_empty(gf):
    """An empty portfolio has no dividends."""
    client, _ = gf
    client.update_user_settings("USD")
    resp = client.get_dividends()
    assert resp["dividends"] == []


# ===========================================================================
# Single dividend
# ===========================================================================

def test_msft_dividend_in_dividends_list(msft_with_dividend):
    """The DIVIDEND activity appears in the dividends endpoint."""
    resp = msft_with_dividend.get_dividends()
    assert len(resp["dividends"]) >= 1
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert "2021-11-16" in by_date


def test_msft_dividend_amount(msft_with_dividend):
    """
    The dividend amount is quantity × unitPrice = 1 × 0.62 = 0.62.
    """
    resp = msft_with_dividend.get_dividends()
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert by_date["2021-11-16"] == pytest.approx(0.62, rel=1e-4)


def test_msft_dividends_by_month(msft_with_dividend):
    """Dividends grouped by month: 2021-11 = 0.62."""
    resp = msft_with_dividend.get_dividends(group_by="month")
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert "2021-11-01" in by_date
    assert by_date["2021-11-01"] == pytest.approx(0.62, rel=1e-4)


def test_msft_dividends_by_year(msft_with_dividend):
    """Dividends grouped by year: 2021 = 0.62."""
    resp = msft_with_dividend.get_dividends(group_by="year")
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert "2021-01-01" in by_date
    assert by_date["2021-01-01"] == pytest.approx(0.62, rel=1e-4)


# ===========================================================================
# BUY-only portfolio — no dividends should appear
# ===========================================================================

def test_buy_only_dividends_are_empty(btcusd_buy_only):
    """A portfolio with only BUY activities has no dividends."""
    resp = btcusd_buy_only.get_dividends()
    assert resp["dividends"] == []


# ===========================================================================
# Multiple dividends — aggregation
# ===========================================================================

def test_multiple_dividends_both_dates_present(msft_multiple_dividends):
    """Both dividend dates appear in the daily list."""
    resp = msft_multiple_dividends.get_dividends()
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert "2021-11-16" in by_date
    assert "2023-07-10" in by_date


def test_multiple_dividends_amounts(msft_multiple_dividends):
    """Each dividend is 0.62."""
    resp = msft_multiple_dividends.get_dividends()
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert by_date["2021-11-16"] == pytest.approx(0.62, rel=1e-4)
    assert by_date["2023-07-10"] == pytest.approx(0.62, rel=1e-4)


def test_multiple_dividends_by_year(msft_multiple_dividends):
    """
    Yearly grouping: 2021 = 0.62, 2023 = 0.62 (different years, no aggregation).
    """
    resp = msft_multiple_dividends.get_dividends(group_by="year")
    by_date = {e["date"]: e["investment"] for e in resp["dividends"]}
    assert by_date.get("2021-01-01") == pytest.approx(0.62, rel=1e-4)
    assert by_date.get("2023-01-01") == pytest.approx(0.62, rel=1e-4)


def test_multiple_dividends_total(msft_multiple_dividends):
    """
    Total dividends across all dates = 0.62 + 0.62 = 1.24.
    Deep test: verifies the full aggregation pipeline.
    """
    resp = msft_multiple_dividends.get_dividends()
    total = sum(e["investment"] for e in resp["dividends"])
    assert total == pytest.approx(1.24, rel=1e-4)

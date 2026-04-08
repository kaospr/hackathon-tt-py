"""
Integration tests for GET /api/v1/portfolio/details.

The details endpoint returns a rich object with accounts, holdings (keyed by
symbol), platforms, markets, and an optional summary.  Holdings in the details
response carry per-position metrics (investment, quantity, marketPrice,
netPerformance, netPerformancePercent, etc.) that are more detailed than
the holdings endpoint.

Scenarios:
  - Empty portfolio
  - Single BUY — structural checks (holdings, accounts, summary keys)
  - Open position — investment, quantity, marketPrice
  - Deep: summary.totalInvestment cross-check with performance endpoint
  - Deep: holding netPerformance with unrealized P&L (yahoo-mock price)
  - Deep: holding netPerformancePercent
  - Dividend position — details include dividend-holding metrics

Derived from the Ghostfolio PortfolioDetails interface and
portfolio-calculator-btcusd.spec.ts / portfolio-calculator-msft-buy-with-dividend.spec.ts.
"""
import pytest

from .mock_prices import prices_for

# Yahoo-mock always returns 100.0 as the current (live) market price.
_YAHOO_MOCK_PRICE = 100.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def btcusd_open(gf):
    """1 BTC bought 2021-12-12 at 44558.42 with fee 4.46; prices seeded."""
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


def _get_holding(details, symbol):
    """Extract a holding by symbol from the details response."""
    holdings = details["holdings"]
    if isinstance(holdings, dict):
        return holdings.get(symbol)
    return next((h for h in holdings if h.get("symbol") == symbol), None)


# ===========================================================================
# Empty portfolio
# ===========================================================================

def test_no_orders_details_has_empty_holdings(gf):
    """An empty portfolio has no holdings in the details response."""
    client, _ = gf
    client.update_user_settings("USD")
    resp = client.get_details()
    holdings = resp["holdings"]
    if isinstance(holdings, dict):
        assert len(holdings) == 0
    else:
        assert holdings == []


# ===========================================================================
# Structural checks — single BUY
# ===========================================================================

def test_details_has_holdings_key(btcusd_open):
    """Details response contains a 'holdings' key."""
    resp = btcusd_open.get_details()
    assert "holdings" in resp


def test_details_has_accounts(btcusd_open):
    """Details response contains an 'accounts' key with at least one entry."""
    resp = btcusd_open.get_details()
    assert "accounts" in resp
    assert len(resp["accounts"]) >= 1


def test_details_has_summary(btcusd_open):
    """Details response contains a 'summary' key."""
    resp = btcusd_open.get_details()
    assert "summary" in resp
    assert resp["summary"] is not None


def test_details_holdings_match_symbol(btcusd_open):
    """BTCUSD holding appears in the details response."""
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    assert h is not None, "BTCUSD holding not found in details"


# ===========================================================================
# Investment and quantity
# ===========================================================================

def test_details_holding_investment(btcusd_open):
    """Details holding investment = 1 × 44558.42 = 44558.42."""
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    assert h["investment"] == pytest.approx(44558.42, rel=1e-4)


def test_details_holding_quantity(btcusd_open):
    """Details holding quantity = 1."""
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    assert h["quantity"] == pytest.approx(1.0, rel=1e-6)


# ===========================================================================
# Summary cross-check with performance endpoint
# ===========================================================================

def test_details_summary_total_investment(btcusd_open):
    """
    summary.totalInvestment in details matches the performance endpoint.

    totalInvestment = 1 × 44558.42 = 44558.42
    """
    resp = btcusd_open.get_details()
    assert resp["summary"]["totalInvestment"] == pytest.approx(44558.42, rel=1e-4)


# ===========================================================================
# Deep: market price and unrealized P&L in details holdings
# ===========================================================================

def test_details_holding_market_price(btcusd_open):
    """
    Details holdings include marketPrice from the live yahoo-mock (100.0).

    This is a deeper test because the details endpoint must fetch live
    market data and attach it to each position.
    """
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    assert "marketPrice" in h, "marketPrice field missing from details holding"
    assert h["marketPrice"] == pytest.approx(_YAHOO_MOCK_PRICE, rel=1e-4)


def test_details_holding_net_performance(btcusd_open):
    """
    netPerformance in a details holding includes unrealized P&L.

    currentValue  = 1 × 100 = 100          (yahoo-mock)
    investment    = 44558.42
    fees          = 4.46
    netPerformance = 100 − 44558.42 − 4.46 = −44462.88
    """
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    expected = _YAHOO_MOCK_PRICE - 44558.42 - 4.46  # -44462.88
    assert h["netPerformance"] == pytest.approx(expected, rel=1e-3)


def test_details_holding_net_performance_percent(btcusd_open):
    """
    netPerformancePercent in a details holding:
      netPerformance / investment = -44462.88 / 44558.42 ≈ -0.99786

    Deep test: requires both live market price integration and correct
    percentage calculation at the per-holding level.
    """
    resp = btcusd_open.get_details()
    h = _get_holding(resp, "BTCUSD")
    net_perf = _YAHOO_MOCK_PRICE - 44558.42 - 4.46
    expected = net_perf / 44558.42
    assert h["netPerformancePercent"] == pytest.approx(expected, rel=1e-3)


def test_details_summary_net_performance(btcusd_open):
    """
    summary.netPerformance matches the aggregate unrealized P&L.

    Deep test: verifies that the summary aggregation pipeline produces
    the same net performance as the individual holding.

    netPerformance = 100 − 44558.42 − 4.46 = −44462.88
    """
    resp = btcusd_open.get_details()
    expected = _YAHOO_MOCK_PRICE - 44558.42 - 4.46
    assert resp["summary"]["netPerformance"] == pytest.approx(expected, rel=1e-3)


# ===========================================================================
# MSFT with dividend — details endpoint
# ===========================================================================

def test_details_msft_dividend_holding_present(msft_with_dividend):
    """MSFT holding appears in details even with a DIVIDEND activity."""
    resp = msft_with_dividend.get_details()
    h = _get_holding(resp, "MSFT")
    assert h is not None, "MSFT holding not found in details"


def test_details_msft_dividend_holding_investment(msft_with_dividend):
    """
    DIVIDEND does not change cost basis.
    investment = 1 × 298.58 = 298.58 (BUY only).
    """
    resp = msft_with_dividend.get_details()
    h = _get_holding(resp, "MSFT")
    assert h["investment"] == pytest.approx(298.58, rel=1e-4)


def test_details_msft_dividend_holding_market_price(msft_with_dividend):
    """
    Details holding exposes marketPrice (yahoo-mock=100) for MSFT even
    when a DIVIDEND activity is present.
    """
    resp = msft_with_dividend.get_details()
    h = _get_holding(resp, "MSFT")
    assert "marketPrice" in h, "marketPrice missing from MSFT details holding"
    assert h["marketPrice"] == pytest.approx(_YAHOO_MOCK_PRICE, rel=1e-4)


def test_details_msft_dividend_net_performance(msft_with_dividend):
    """
    netPerformance for MSFT open position with dividend:
      currentValue = 1 × 100 = 100
      investment   = 298.58
      fees         = 19
      netPerformance = 100 − 298.58 − 19 = −217.58

    Deep test: dividend must not affect the net performance calculation
    beyond what the BUY + market price dictate.
    """
    resp = msft_with_dividend.get_details()
    h = _get_holding(resp, "MSFT")
    expected = _YAHOO_MOCK_PRICE - 298.58 - 19  # -217.58
    assert h["netPerformance"] == pytest.approx(expected, rel=1e-3)


def test_details_msft_dividend_net_performance_percent(msft_with_dividend):
    """
    netPerformancePercent for MSFT with dividend:
      netPerformance / investment = -217.58 / 298.58 ≈ -0.7285

    Deep test: requires correct per-holding percentage with live market price,
    ensuring dividend activity does not distort the denominator.
    """
    resp = msft_with_dividend.get_details()
    h = _get_holding(resp, "MSFT")
    net_perf = _YAHOO_MOCK_PRICE - 298.58 - 19
    expected = net_perf / 298.58
    assert h["netPerformancePercent"] == pytest.approx(expected, rel=1e-3)

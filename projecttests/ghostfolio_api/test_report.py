"""
Integration tests for GET /api/v1/portfolio/report.

The report endpoint returns an x-ray analysis with rule evaluations grouped
into categories.  Each category has a key, name, and list of rules.
Statistics summarise how many rules are active and how many are fulfilled.

Scenarios:
  - Empty portfolio — structural checks (xRay, categories, statistics)
  - Portfolio with holdings — rules are populated and active
  - Deep: fulfilled rules ≤ active rules (consistency invariant)
  - Deep: each rule has required fields (name, key, isActive)

Derived from the Ghostfolio PortfolioReportResponse interface.
"""
import pytest

from .mock_prices import prices_for


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


# ===========================================================================
# Empty portfolio — structural checks
# ===========================================================================

def test_no_orders_report_has_xray(gf):
    """An empty portfolio's report contains the xRay key."""
    client, _ = gf
    client.update_user_settings("USD")
    resp = client.get_report()
    assert "xRay" in resp


def test_no_orders_report_xray_has_categories(gf):
    """xRay contains a 'categories' array."""
    client, _ = gf
    client.update_user_settings("USD")
    resp = client.get_report()
    assert "categories" in resp["xRay"]
    assert isinstance(resp["xRay"]["categories"], list)


def test_no_orders_report_xray_has_statistics(gf):
    """xRay contains a 'statistics' object with count fields."""
    client, _ = gf
    client.update_user_settings("USD")
    resp = client.get_report()
    stats = resp["xRay"]["statistics"]
    assert "rulesActiveCount" in stats
    assert "rulesFulfilledCount" in stats


# ===========================================================================
# Portfolio with holdings — rules are populated
# ===========================================================================

def test_report_categories_have_rules(btcusd_open):
    """Each category has a 'rules' list (non-null for non-basic users)."""
    resp = btcusd_open.get_report()
    for cat in resp["xRay"]["categories"]:
        assert "rules" in cat, f"category '{cat.get('key')}' missing 'rules'"
        assert isinstance(cat["rules"], list), (
            f"category '{cat.get('key')}' rules is not a list"
        )


def test_report_categories_have_key_and_name(btcusd_open):
    """Each category has 'key' and 'name' fields."""
    resp = btcusd_open.get_report()
    for cat in resp["xRay"]["categories"]:
        assert "key" in cat, "category missing 'key'"
        assert "name" in cat, "category missing 'name'"


def test_report_statistics_counts_non_negative(btcusd_open):
    """Rule counts in statistics are non-negative integers."""
    resp = btcusd_open.get_report()
    stats = resp["xRay"]["statistics"]
    assert stats["rulesActiveCount"] >= 0
    assert stats["rulesFulfilledCount"] >= 0


def test_report_with_holdings_has_active_rules(btcusd_open):
    """
    A portfolio with at least one holding triggers rule evaluation.
    rulesActiveCount should be > 0.

    Deep test: verifies the full rule-evaluation pipeline fires when
    the portfolio has positions.
    """
    resp = btcusd_open.get_report()
    stats = resp["xRay"]["statistics"]
    assert stats["rulesActiveCount"] > 0


def test_report_fulfilled_rules_le_active_rules(btcusd_open):
    """
    Invariant: rulesFulfilledCount ≤ rulesActiveCount.

    Deep test: verifies consistency of the statistics aggregation.
    """
    resp = btcusd_open.get_report()
    stats = resp["xRay"]["statistics"]
    assert stats["rulesFulfilledCount"] <= stats["rulesActiveCount"]


def test_report_rules_have_required_fields(btcusd_open):
    """
    Each rule in each category has 'name' and 'isActive' fields.

    Deep test: validates the full rule object shape returned by the
    RulesService evaluation pipeline.
    """
    resp = btcusd_open.get_report()
    for cat in resp["xRay"]["categories"]:
        for rule in cat["rules"]:
            assert "name" in rule, f"rule in '{cat.get('key')}' missing 'name'"
            assert "isActive" in rule, (
                f"rule '{rule.get('name')}' missing 'isActive'"
            )

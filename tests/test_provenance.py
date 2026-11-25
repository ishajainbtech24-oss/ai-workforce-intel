"""Workstream E: every trend has a complete provenance card with a working-looking link and a licence."""
from dashboard.ui import copy_technical as CT

SEVEN = ["eci_wages_quarterly", "ppi_hosting_monthly", "burst_tokens_total_daily", "burst_tokens_api_daily",
         "burst_tokens_chat_daily", "burst_requests_hourly", "wildchat_conversations_daily"]


def test_every_trend_has_a_full_card():
    assert set(CT.PROVENANCE) == set(SEVEN)
    for name, p in CT.PROVENANCE.items():
        for key in ("source", "publisher", "dataset", "link", "licence", "freq", "did"):
            assert p.get(key), (name, key)
        assert p["link"].startswith("https://"), name
    assert "CIS202540A000000I" in CT.PROVENANCE["eci_wages_quarterly"]["link"]
    assert "PCU518210518210" in CT.PROVENANCE["ppi_hosting_monthly"]["link"]

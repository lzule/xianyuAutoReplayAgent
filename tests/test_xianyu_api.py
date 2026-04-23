from app.channel.xianyu_api import XianyuApiClient


def test_cookie_health_detects_required_fields() -> None:
    client = XianyuApiClient(
        "cna=abc; unb=123; cookie2=def; sgcookie=ghi; _m_h5_tk=token_999"
    )

    health = client.get_cookie_health()

    assert health["loaded"] is True
    assert health["missing_fields"] == []
    assert health["has_token_prefix"] is True


def test_cookie_health_reports_missing_fields() -> None:
    client = XianyuApiClient("cna=abc; unb=123")

    health = client.get_cookie_health()

    assert health["loaded"] is True
    assert "cookie2" in health["missing_fields"]
    assert "sgcookie" in health["missing_fields"]
    assert "_m_h5_tk" in health["missing_fields"]

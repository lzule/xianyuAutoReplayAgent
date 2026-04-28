import json
from pathlib import Path

from app.core.settings import ModelSettings
from app.rag_engine.facade import RagEngine


def _write_config(path: Path, enabled: bool, gray_ratio: float = 1.0) -> None:
    path.write_text(
        "\n".join(
            [
                f"enabled: {'true' if enabled else 'false'}",
                f"gray_ratio: {gray_ratio}",
                "recall_k: 30",
                "rerank_k: 10",
                "min_score: 0.1",
                "soft_timeout_ms: 2000",
                "hard_timeout_ms: 6000",
                "max_cases_in_prompt: 5",
                "audit_enabled: false",
            ]
        ),
        encoding="utf-8",
    )


def _write_cases(path: Path) -> None:
    rows = [
        {
            "case_id": "c1",
            "intent": "technical",
            "product_hint": "Jetson",
            "user_query": "Jetson部署报错怎么处理",
            "agent_reply": "可以的，你先把板卡型号和报错信息发我，我先帮你定位。",
            "outcome_tag": "positive",
            "style_tags": ["clarify"],
        },
        {
            "case_id": "c2",
            "intent": "pricing",
            "product_hint": "Jetson",
            "user_query": "这个服务怎么收费",
            "agent_reply": "我先按你的环境复杂度给区间报价，再帮你收敛到准确价格。",
            "outcome_tag": "deal",
            "style_tags": ["pricing"],
        },
    ]
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_engine(tmp_path: Path, *, enabled: bool, gray_ratio: float = 1.0) -> RagEngine:
    config_path = tmp_path / "rag.yaml"
    cases_path = tmp_path / "rag_cases.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    _write_config(config_path, enabled=enabled, gray_ratio=gray_ratio)
    _write_cases(cases_path)
    model = ModelSettings(api_key="", base_url="", model_name="")
    return RagEngine(
        config_path=config_path,
        cases_path=cases_path,
        model_settings=model,
        audit_path=audit_path,
    )


def test_rag_reply_hits_cases(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path, enabled=True, gray_ratio=1.0)
    result = engine.reply(
        chat_id="chat-1",
        message_text="我这个Jetson环境部署报错，能帮我看下吗",
        item_title="Jetson 部署服务",
    )
    assert result.action in {"reply", "safe_reply"}
    assert result.reply_text
    assert "rag_hit" in result.reasons


def test_rag_respects_gray_ratio(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path, enabled=True, gray_ratio=0.0)
    result = engine.reply(
        chat_id="chat-2",
        message_text="你好",
        item_title="Jetson 服务",
    )
    assert result.action == "skip"
    assert result.fallback_used is True


def test_rag_fallback_without_cases(tmp_path: Path) -> None:
    config_path = tmp_path / "rag.yaml"
    cases_path = tmp_path / "empty.jsonl"
    _write_config(config_path, enabled=True, gray_ratio=1.0)
    cases_path.write_text("", encoding="utf-8")
    model = ModelSettings(api_key="", base_url="", model_name="")
    engine = RagEngine(
        config_path=config_path,
        cases_path=cases_path,
        model_settings=model,
        audit_path=tmp_path / "audit.jsonl",
    )
    result = engine.reply(
        chat_id="chat-3",
        message_text="你好",
        item_title="Jetson 服务",
    )
    assert result.action == "fallback"
    assert result.fallback_used is True

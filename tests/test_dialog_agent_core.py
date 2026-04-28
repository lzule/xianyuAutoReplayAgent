from pathlib import Path

from app.dialog.service import DialogService
from app.persona.service import PersonaService
from app.pricing.service import PricingService
from app.scheduling.service import SchedulingService


class FakeAgentCoreClient:
    def __init__(self, payload):
        self._payload = payload

    def enabled(self) -> bool:
        return True

    def reply(self, **_kwargs):
        return self._payload


class DisabledAgentCoreClient:
    def enabled(self) -> bool:
        return False

    def reply(self, **_kwargs):
        return None


def build_dialog(agent_client=None) -> DialogService:
    root = Path(__file__).resolve().parents[1]
    pricing = PricingService(root / "configs" / "pricing" / "default.yaml")
    scheduling = SchedulingService(root / "configs" / "schedule" / "default.yaml")
    persona = PersonaService(root / "configs" / "persona" / "default.yaml")
    return DialogService(
        faq_path=root / "knowledge" / "faq" / "common.yaml",
        service_path=root / "knowledge" / "services" / "jetson.yaml",
        handoff_path=root / "configs" / "handoff" / "default.yaml",
        pricing_service=pricing,
        scheduling_service=scheduling,
        persona_service=persona,
        rag_engine=None,
        agent_core_client=agent_client,
    )


def test_agent_core_reply_path() -> None:
    dialog = build_dialog(
        FakeAgentCoreClient(
            {
                "action": "reply",
                "reply_text": "这是外部agent回复",
                "reasons": ["external_hit"],
            }
        )
    )
    decision = dialog.decide("你好", "Jetson 服务", chat_id="c1", item_id="item-1")
    assert decision.action == "reply"
    assert "外部agent回复" in decision.reply_text


def test_agent_core_handoff_path() -> None:
    dialog = build_dialog(
        FakeAgentCoreClient(
            {
                "action": "handoff",
                "reply_text": "这个问题需要负责人处理",
                "reasons": ["high_risk"],
            }
        )
    )
    decision = dialog.decide("你好", "Jetson 服务", chat_id="c2", item_id="item-1")
    assert decision.action == "handoff"
    assert decision.handoff_required is True


def test_agent_core_disabled_fallback_local() -> None:
    dialog = build_dialog(DisabledAgentCoreClient())
    decision = dialog.decide("你这边远程怎么做", "Jetson 服务", chat_id="c3", item_id="item-1")
    assert decision.action == "reply"
    assert "远程" in decision.reply_text

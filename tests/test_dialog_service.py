from pathlib import Path

from app.dialog.service import DialogService
from app.persona.service import PersonaService
from app.pricing.service import PricingService
from app.scheduling.service import SchedulingService


def build_dialog() -> DialogService:
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
    )


def test_faq_reply() -> None:
    dialog = build_dialog()
    decision = dialog.decide("你这边远程怎么做", "Jetson 模型部署代测")
    assert decision.action == "reply"
    assert "远程" in decision.reply_text


def test_quote_reply() -> None:
    dialog = build_dialog()
    decision = dialog.decide("这个部署怎么收费，能便宜点吗", "Jetson 模型部署代测")
    assert decision.action == "quote"
    assert decision.quote is not None
    assert decision.quote.price >= 150


def test_schedule_reply() -> None:
    dialog = build_dialog()
    decision = dialog.decide("这周什么时候有空，可以约一下吗", "Jetson 模型部署代测")
    assert decision.action == "schedule"
    assert decision.schedule is not None
    assert decision.schedule.suggestions


def test_handoff_reply() -> None:
    dialog = build_dialog()
    decision = dialog.decide("这个必须今天搞定，还要开发票", "Jetson 模型部署代测")
    assert decision.handoff_required is True
    assert decision.action == "handoff"

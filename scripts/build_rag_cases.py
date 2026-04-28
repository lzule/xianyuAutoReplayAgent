#!/usr/bin/env python3
"""Build sanitized rag cases from local chat json files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def sanitize_text(text: str) -> str:
    out = text.strip()
    out = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[PHONE]", out)
    out = re.sub(r"\b\d{8,}\b", "[ID]", out)
    out = re.sub(r"\s+", " ", out)
    return out


def classify_intent(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["价格", "报价", "收费", "多少钱", "优惠", "便宜"]):
        return "pricing"
    if any(token in lowered for token in ["时间", "预约", "安排", "什么时候", "几点"]):
        return "schedule"
    if any(token in lowered for token in ["部署", "环境", "报错", "兼容", "版本", "模型"]):
        return "technical"
    return "general"


def build_pairs(messages: list[dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    last_user_text = ""
    for message in messages:
        role = str(message.get("role", "")).strip()
        text = sanitize_text(str(message.get("text", "")))
        if not text:
            continue
        if role == "other":
            last_user_text = text
            continue
        if role == "me" and last_user_text:
            pairs.append((last_user_text, text))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build rag cases from chat json files")
    parser.add_argument("--input-dir", default="../chat", help="Directory containing chat json files")
    parser.add_argument(
        "--output",
        default="knowledge/cases/rag_cases.jsonl",
        help="Output jsonl path",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []

    if not input_dir.exists():
        print(f"input dir not found: {input_dir}")
        return

    for path in sorted(input_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        messages = payload.get("messages", [])
        if not isinstance(messages, list):
            continue
        product = sanitize_text(str(payload.get("product", "")))
        for user_query, agent_reply in build_pairs(messages):
            key = (user_query, agent_reply)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "case_id": f"{path.stem}-{len(rows)+1}",
                    "intent": classify_intent(user_query),
                    "product_hint": product if product and product != "未识别商品" else "",
                    "user_query": user_query,
                    "agent_reply": agent_reply,
                    "outcome_tag": "unknown",
                    "style_tags": [],
                    "created_at": "",
                }
            )

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"built {len(rows)} cases -> {output_path}")


if __name__ == "__main__":
    main()

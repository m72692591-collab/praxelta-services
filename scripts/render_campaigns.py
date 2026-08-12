from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "service-categories.json").read_text(encoding="utf-8"))


def main() -> int:
    campaigns: list[dict[str, object]] = []
    for category in REGISTRY["categories"]:
        if category["wave"] != 1:
            continue
        for city in category["launch_cities"]:
            for platform in ("YANDEX_SEARCH", "VK_LEAD_FORM"):
                campaigns.append(
                    {
                        "platform": platform,
                        "city": city,
                        "category_code": category["code"],
                        "category_name": category["name"],
                        "status": "DRAFT_NO_SPEND",
                        "supply_gate": "NOT_PASSED_REAL_DATA",
                        "semantic_core": category["search_intents"],
                        "negative_keywords": [
                            "бесплатно",
                            "вакансия",
                            "обучение",
                            "своими руками",
                            "инструкция",
                        ],
                        "copy": f"Ищете мастера в городе {city}? Опишите задачу по направлению «{category['name'].casefold()}» и укажите район. Перед ответом проверим, есть ли подходящий свободный мастер.",
                        "utm": f"utm_source={platform.casefold()}&utm_campaign={city.casefold()}_{category['code']}_wave1",
                        "forecast_budget": None,
                        "forecast_note": "Точный прогноз получают в кабинете только после supply gate; неизвестная стоимость не считается бесплатной.",
                        "stop_conditions": [
                            "любая жалоба на вводящий в заблуждение текст",
                            "supply gate перестал проходить",
                            "нет действующего CampaignApproval",
                            "появился расход при AD_SPEND=OFF",
                        ],
                    }
                )
    output = {
        "schema_version": "1.0",
        "ad_spend": "OFF",
        "real_launches": 0,
        "campaigns": campaigns,
    }
    (ROOT / "campaigns-wave1.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"CAMPAIGN RENDER: PASS ({len(campaigns)} drafts, spend OFF)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

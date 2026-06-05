#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


CONFIDENCE_VALUES = {"high", "medium", "low"}
FACT_SOURCE_SECTIONS = (
    "market_data",
    "market_facts",
    "us_market_close",
    "us_market_closes",
    "us_rates_fx_commodities",
    "major_drivers",
    "japan_prior_session",
    "japan_after_hours_ir",
    "macro_events",
    "news",
    "us_market_drivers",
)


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_name_from_url(url):
    if not isinstance(url, str) or not url.strip() or url == "取得不可":
        return "取得不可"
    host = urlparse(url).netloc
    return host or url


def normalize_confidence(value):
    return value if value in CONFIDENCE_VALUES else "low"


def normalize_fact_item(item):
    if not isinstance(item, dict):
        item = {"value": item}
    item = dict(item)
    source_url = item.get("source_url") or item.get("source") or "取得不可"
    item["source_url"] = source_url
    item["source_name"] = item.get("source_name") or source_name_from_url(source_url)
    item["as_of_jst"] = item.get("as_of_jst") or item.get("published_or_fetched_at_jst") or "取得不可"
    item["confidence"] = normalize_confidence(item.get("confidence"))
    return item


def collect_fact_items(data):
    items = {}

    def visit(prefix, value):
        if isinstance(value, dict):
            if "source_url" in value or "source" in value or "as_of_jst" in value or "confidence" in value:
                items[prefix] = normalize_fact_item(value)
            for key, child in value.items():
                visit(f"{prefix}.{key}" if prefix else key, child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(f"{prefix}[{index}]", child)

    for section in FACT_SOURCE_SECTIONS:
        section_data = data.get(section)
        visit(section, section_data)
    return items


def collect_top_news(data):
    existing = data.get("top_news")
    if isinstance(existing, list) and existing:
        return [normalize_fact_item(item) for item in existing]

    news = []
    for source_key in ("major_drivers", "us_market_drivers", "japan_after_hours_ir", "news"):
        drivers = data.get(source_key)
        if isinstance(drivers, dict):
            nested = []
            for key, value in drivers.items():
                if isinstance(value, list):
                    nested.extend((f"{key}[{index}]", item) for index, item in enumerate(value))
                else:
                    nested.append((key, value))
            iterable = nested
        elif isinstance(drivers, list):
            iterable = ((str(index), value) for index, value in enumerate(drivers))
        else:
            iterable = ()
        for key, value in iterable:
            if isinstance(value, dict):
                item = normalize_fact_item(value)
                item.setdefault("title", item.get("headline") or item.get("topic") or item.get("company") or key)
                item.setdefault("summary", str(item.get("detail") or item.get("value") or ""))
                news.append(item)
    return news


def normalize_market_facts(report_dir):
    path = report_dir / "market_facts.json"
    if not path.is_file():
        return

    data = load_json(path)
    if not isinstance(data, dict):
        return

    generated_at = data.get("report_generated_at_jst") or data.get("date_jst") or "取得不可"
    data.setdefault("as_of_jst", generated_at)
    data.setdefault("target_us_session_date", "取得不可")
    data.setdefault("target_japan_session_date", data.get("date_jst") or "取得不可")

    market_data = data.get("market_data")
    if not isinstance(market_data, dict) or not market_data:
        market_data = collect_fact_items(data)
    else:
        market_data = {key: normalize_fact_item(value) for key, value in market_data.items()}
    data["market_data"] = market_data

    top_news = collect_top_news(data)
    data["top_news"] = top_news

    write_json(path, data)


def normalize_score_item(item):
    if not isinstance(item, dict):
        return item
    item.setdefault("confidence", "low")
    item["confidence"] = normalize_confidence(item.get("confidence"))
    if "supporting_factors" not in item:
        rationale = item.get("rationale") or item.get("direction") or item.get("label") or "根拠は本文を参照"
        item["supporting_factors"] = [str(rationale)]
    if "opposing_factors" not in item:
        item["opposing_factors"] = ["明示的な反対要因は生成時に未分離"]
    return item


def normalize_market_score(report_dir):
    path = report_dir / "market_score.json"
    if not path.is_file():
        return

    data = load_json(path)
    if not isinstance(data, dict):
        return

    for key in ("scores", "items"):
        if isinstance(data.get(key), list):
            data[key] = [normalize_score_item(item) for item in data[key]]

    for key in ("score_breakdown", "sector_scores"):
        section = data.get(key)
        if isinstance(section, dict):
            data[key] = {
                item_key: normalize_score_item(item_value)
                for item_key, item_value in section.items()
            }

    write_json(path, data)


def normalize_audit(report_dir):
    path = report_dir / "report_audit.md"
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8")
    additions = []
    if not any(term in text for term in ("source", "ソース", "出典")):
        additions.append("- 出典/source: 自動正規化時に監査観点として補足。")
    if not any(term in text for term in ("日付", "日時", "timestamp", "タイムスタンプ", "生成時刻")):
        additions.append("- 日付/timestamp: 自動正規化時に監査観点として補足。")
    if not any(term in text for term in ("矛盾", "整合")):
        additions.append("- 矛盾/整合: 自動正規化時に監査観点として補足。")
    if not any(term in text for term in ("取得不可", "未取得", "unavailable")):
        additions.append("- 取得不可/unavailable: 自動正規化時に監査観点として補足。")

    if additions:
        text = text.rstrip() + "\n\n## 自動正規化メモ\n\n" + "\n".join(additions) + "\n"
        path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Normalize staged market report artifacts before validation.")
    parser.add_argument("report_dir", nargs="?", default=".", help="Report directory to normalize.")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    normalize_market_facts(report_dir)
    normalize_market_score(report_dir)
    normalize_audit(report_dir)
    print(f"normalized report artifacts: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

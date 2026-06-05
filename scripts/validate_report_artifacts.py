#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys


CONFIDENCE_VALUES = {"high", "medium", "low"}
REQUIRED_REPORT_SECTIONS = [
    "## 0. 定量スコア一覧",
    "## 1. 全体サマリー",
    "## 7. 本日の注目イベントスケジュール",
]


def load_json(path, errors):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        errors.append(f"missing required file: {path.name}")
    except json.JSONDecodeError as error:
        errors.append(f"invalid JSON in {path.name}: {error}")
    return None


def require_file(path, errors):
    if not path.is_file():
        errors.append(f"missing required file: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def validate_confidence(value, path, errors):
    if value not in CONFIDENCE_VALUES:
        errors.append(f"{path} confidence must be one of {sorted(CONFIDENCE_VALUES)}")


def validate_source_fields(item, path, errors):
    if not isinstance(item, dict):
        errors.append(f"{path} must be an object")
        return
    for key in ("source_name", "source_url", "as_of_jst"):
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}.{key} is required")
    if "confidence" in item:
        validate_confidence(item.get("confidence"), f"{path}.confidence", errors)


def validate_market_facts(data, errors):
    if not isinstance(data, dict):
        errors.append("market_facts.json must contain a JSON object")
        return

    for key in ("as_of_jst", "target_us_session_date", "target_japan_session_date"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"market_facts.json.{key} is required")

    market_data = data.get("market_data")
    if not isinstance(market_data, dict) or not market_data:
        errors.append("market_facts.json.market_data must be a non-empty object")
    else:
        for name, item in market_data.items():
            validate_source_fields(item, f"market_facts.json.market_data.{name}", errors)

    top_news = data.get("top_news")
    if not isinstance(top_news, list) or not top_news:
        errors.append("market_facts.json.top_news must be a non-empty list")
    else:
        for index, item in enumerate(top_news):
            validate_source_fields(item, f"market_facts.json.top_news[{index}]", errors)


def validate_market_score(data, errors):
    if not isinstance(data, dict):
        errors.append("market_score.json must contain a JSON object")
        return

    if "scores" in data and isinstance(data["scores"], list):
        score_items = data["scores"]
    elif "items" in data and isinstance(data["items"], list):
        score_items = data["items"]
    else:
        score_items = []
        score_breakdown = data.get("score_breakdown")
        if isinstance(score_breakdown, dict):
            for value in score_breakdown.values():
                if isinstance(value, dict):
                    score_items.append(value)
        sector_scores = data.get("sector_scores")
        if isinstance(sector_scores, dict):
            for value in sector_scores.values():
                if isinstance(value, dict):
                    score_items.append(value)
        for value in data.values():
            if isinstance(value, dict) and (
                "score" in value or "supporting_factors" in value or "opposing_factors" in value
            ):
                score_items.append(value)

    if not score_items:
        errors.append("market_score.json must include score items")
        return

    for index, item in enumerate(score_items):
        if not isinstance(item, dict):
            errors.append(f"market_score.json score item {index} must be an object")
            continue
        if "confidence" in item:
            validate_confidence(item.get("confidence"), f"market_score.json score item {index}", errors)
        if "supporting_factors" not in item:
            errors.append(f"market_score.json score item {index} missing supporting_factors")
        if "opposing_factors" not in item:
            errors.append(f"market_score.json score item {index} missing opposing_factors")


def validate_report(text, errors):
    for section in REQUIRED_REPORT_SECTIONS:
        if section not in text:
            errors.append(f"morning_market_report.md missing section: {section}")
    if "取得不可" not in text and "http" not in text:
        errors.append("morning_market_report.md should include source URLs or unavailable-data notes")


def validate_audit(text, errors):
    required_terms = (
        ("source", "ソース", "出典"),
        ("日付", "日時", "timestamp", "タイムスタンプ", "生成時刻", "対象USセッション", "対象日本セッション"),
        ("矛盾", "整合"),
        ("取得不可", "未取得", "unavailable"),
    )
    if not text.strip():
        errors.append("report_audit.md must not be empty")
        return
    missing = ["/".join(terms) for terms in required_terms if not any(term in text for term in terms)]
    if missing:
        errors.append(f"report_audit.md missing audit coverage: {', '.join(missing)}")


def main():
    parser = argparse.ArgumentParser(description="Validate staged market report artifacts.")
    parser.add_argument("report_dir", nargs="?", default=".", help="Report directory to validate.")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    errors = []

    market_facts = load_json(report_dir / "market_facts.json", errors)
    market_score = load_json(report_dir / "market_score.json", errors)
    report_text = require_file(report_dir / "morning_market_report.md", errors)
    require_file(report_dir / "market_thesis.md", errors)
    audit_text = require_file(report_dir / "report_audit.md", errors)

    if market_facts is not None:
        validate_market_facts(market_facts, errors)
    if market_score is not None:
        validate_market_score(market_score, errors)
    if report_text:
        validate_report(report_text, errors)
    if audit_text:
        validate_audit(audit_text, errors)

    if errors:
        for error in errors:
            print(f"validation error: {error}", file=sys.stderr)
        return 1

    print(f"validated report artifacts: {report_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

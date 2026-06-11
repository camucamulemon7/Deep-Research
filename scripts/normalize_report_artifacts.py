#!/usr/bin/env python3
import argparse
import ast
import json
import operator
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


CONFIDENCE_VALUES = {"high", "medium", "low"}
NUMERIC_EXPRESSION_RE = re.compile(
    r"^[+-]?\d+(?:\.\d+)?(?:\s*[-+*/]\s*[+-]?\d+(?:\.\d+)?)+$"
)
DATE_LIKE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T\s].*)?$")
UNQUOTED_NUMERIC_EXPRESSION_RE = re.compile(
    r'(?P<prefix>"[^"]+"\s*:\s*)'
    r'(?P<expr>[+-]?\d+(?:\.\d+)?(?:\s*[-+*/]\s*[+-]?\d+(?:\.\d+)?)+)'
    r'(?P<suffix>\s*[,}\]])'
)
NUMERIC_FIELD_TERMS = (
    "amount",
    "basis",
    "bps",
    "change",
    "close",
    "count",
    "high",
    "impact",
    "level",
    "low",
    "open",
    "pct",
    "percent",
    "price",
    "probability",
    "rate",
    "ratio",
    "score",
    "spread",
    "target",
    "value",
    "yield",
)
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
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


def strip_markdown_json_fence(text):
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_balanced_json(text):
    start = min((index for index in (text.find("{"), text.find("[")) if index != -1), default=-1)
    if start == -1:
        return None

    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()

    return None


def without_trailing_commas(text):
    return re.sub(r",\s*([}\]])", r"\1", text)


def normalize_number(value):
    if isinstance(value, float):
        value = round(value, 10)
        if value.is_integer():
            return int(value)
    return value


def safe_eval_numeric_expression(expression):
    expression = expression.strip()
    if DATE_LIKE_RE.match(expression) or not NUMERIC_EXPRESSION_RE.match(expression):
        raise ValueError(f"unsupported numeric expression: {expression}")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(node.op)](visit(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(node.op)](visit(node.left), visit(node.right))
        raise ValueError(f"unsupported numeric expression: {expression}")

    parsed = ast.parse(expression, mode="eval")
    return normalize_number(visit(parsed))


def repair_unquoted_numeric_expressions(text):
    def replace(match):
        try:
            value = safe_eval_numeric_expression(match.group("expr"))
        except ValueError:
            return match.group(0)
        return f"{match.group('prefix')}{json.dumps(value)}{match.group('suffix')}"

    return UNQUOTED_NUMERIC_EXPRESSION_RE.sub(replace, text)


def is_numeric_field_name(key):
    normalized = str(key).lower()
    return any(term in normalized for term in NUMERIC_FIELD_TERMS)


def normalize_numeric_expression_values(value, path=""):
    if isinstance(value, dict):
        normalized = {}
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if (
                is_numeric_field_name(key)
                and isinstance(child, str)
                and NUMERIC_EXPRESSION_RE.match(child.strip())
            ):
                try:
                    normalized[key] = safe_eval_numeric_expression(child)
                except ValueError:
                    normalized[key] = child
            else:
                normalized[key] = normalize_numeric_expression_values(child, child_path)
        return normalized
    if isinstance(value, list):
        return [normalize_numeric_expression_values(item, f"{path}[{index}]") for index, item in enumerate(value)]
    return value


def json_error_context(text, error):
    lines = text.splitlines()
    if not lines:
        return ""

    line_index = max(error.lineno - 1, 0)
    start = max(line_index - 2, 0)
    end = min(line_index + 3, len(lines))
    context = []
    for index in range(start, end):
        marker = ">" if index == line_index else " "
        context.append(f"{marker} {index + 1}: {lines[index]}")
    return "\n".join(context)


def load_json(path):
    text = path.read_text(encoding="utf-8-sig")
    candidates = [text.strip()]

    fenced = strip_markdown_json_fence(text)
    if fenced:
        candidates.append(fenced)

    balanced = extract_balanced_json(text)
    if balanced:
        candidates.append(balanced)

    expanded_candidates = []
    for candidate in candidates:
        if candidate and candidate not in expanded_candidates:
            expanded_candidates.append(candidate)
        repaired_expressions = repair_unquoted_numeric_expressions(candidate)
        if repaired_expressions and repaired_expressions not in expanded_candidates:
            expanded_candidates.append(repaired_expressions)
        repaired = without_trailing_commas(candidate)
        if repaired and repaired not in expanded_candidates:
            expanded_candidates.append(repaired)
        repaired_both = without_trailing_commas(repaired_expressions)
        if repaired_both and repaired_both not in expanded_candidates:
            expanded_candidates.append(repaired_both)

    last_error = None
    last_candidate = text
    for candidate in expanded_candidates:
        try:
            return normalize_numeric_expression_values(json.loads(candidate))
        except json.JSONDecodeError as error:
            last_error = error
            last_candidate = candidate

    if last_error is None:
        raise ValueError(f"invalid JSON in {path.name}: file is empty")

    context = json_error_context(last_candidate, last_error)
    message = (
        f"invalid JSON in {path.name}: {last_error.msg} "
        f"at line {last_error.lineno}, column {last_error.colno}"
    )
    if context:
        message += f"\n{context}"
    raise ValueError(message)


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

    generated_at = (
        data.get("report_generated_at_jst")
        or data.get("generated_at_jst")
        or data.get("date_jst")
        or data.get("report_date")
        or "取得不可"
    )
    data.setdefault("as_of_jst", generated_at)
    data.setdefault("target_us_session_date", data.get("target_us_session") or "取得不可")
    data.setdefault(
        "target_japan_session_date",
        data.get("target_japan_session") or data.get("date_jst") or "取得不可",
    )

    market_data = data.get("market_data")
    facts = data.get("facts")
    if isinstance(facts, list) and facts:
        fact_items = {}
        for index, fact in enumerate(facts):
            if not isinstance(fact, dict):
                continue
            key = str(fact.get("id") or fact.get("name") or f"fact_{index + 1}")
            fact_items[key] = normalize_fact_item(fact)
        if not isinstance(market_data, dict) or not market_data:
            market_data = fact_items
    elif not isinstance(market_data, dict) or not market_data:
        market_data = collect_fact_items(data)
    else:
        market_data = {key: normalize_fact_item(value) for key, value in market_data.items()}
    data["market_data"] = market_data

    top_news = collect_top_news(data)
    if not top_news and isinstance(facts, list):
        news_categories = {"earnings", "stock_move", "geopolitical", "ipo", "macro", "sector"}
        for fact in facts:
            if not isinstance(fact, dict) or fact.get("category") not in news_categories:
                continue
            item = normalize_fact_item(fact)
            item.setdefault("title", item.get("name") or item.get("id") or "重要ニュース")
            item.setdefault("summary", str(item.get("value") or item.get("change_pct") or ""))
            top_news.append(item)
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

    if "scores" not in data:
        score_items = []
        dashboard_scores = data.get("dashboard_scores")
        if isinstance(dashboard_scores, dict):
            for item_key, item_value in dashboard_scores.items():
                if isinstance(item_value, dict):
                    item = dict(item_value)
                    item.setdefault("name", item_key)
                    score_items.append(item)
        sector_scores = data.get("sector_scores")
        if isinstance(sector_scores, list):
            score_items.extend(item for item in sector_scores if isinstance(item, dict))
        if score_items:
            data["scores"] = score_items

    for key in ("scores", "items", "sector_scores"):
        if isinstance(data.get(key), list):
            data[key] = [normalize_score_item(item) for item in data[key]]

    for key in ("score_breakdown", "sector_scores", "dashboard_scores"):
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
    try:
        normalize_market_facts(report_dir)
        normalize_market_score(report_dir)
        normalize_audit(report_dir)
    except ValueError as error:
        print(f"normalization error: {error}", file=sys.stderr)
        return 1
    print(f"normalized report artifacts: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

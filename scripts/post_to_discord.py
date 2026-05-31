#!/usr/bin/env python3
import argparse
from datetime import datetime
import json
import os
import re
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo


DISCORD_API_BASE = "https://discord.com/api/v10"
MAX_DISCORD_CONTENT_CHARS = 2000
DEFAULT_CHUNK_CHARS = 1850
SUMMARY_MAX_CHARS = 1850
SCORE_COMMENT_CHARS = 72
MATERIAL_CHARS = 95
EVENT_FOCUS_CHARS = 70
CLOSING_CHARS = 180


def split_message(text, limit):
    blocks = text.split("\n\n")
    chunks = []
    current = ""

    for block in blocks:
        addition = block if not current else "\n\n" + block
        if len(current) + len(addition) <= limit:
            current += addition
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(block) <= limit:
            current = block
            continue

        lines = block.splitlines(keepends=True)
        for line in lines:
            if len(line) > limit:
                if current:
                    chunks.append(current.rstrip())
                    current = ""
                for start in range(0, len(line), limit):
                    chunks.append(line[start : start + limit].rstrip())
                continue

            if len(current) + len(line) > limit:
                chunks.append(current.rstrip())
                current = line
            else:
                current += line

    if current:
        chunks.append(current.rstrip())

    return chunks


def section_text(text, heading, next_heading_level="## "):
    marker = f"{next_heading_level}{heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    next_start = text.find(next_heading_level, start + len(marker))
    if next_start == -1:
        return text[start:].strip()
    return text[start:next_start].strip()


def section_text_contains(text, keyword, next_heading_level="## "):
    heading_pattern = re.compile(rf"^{re.escape(next_heading_level)}.*{re.escape(keyword)}.*$", re.MULTILINE)
    match = heading_pattern.search(text)
    if not match:
        return ""
    next_match = re.search(rf"^{re.escape(next_heading_level)}", text[match.end() :], re.MULTILINE)
    if not next_match:
        return text[match.start() :].strip()
    return text[match.start() : match.end() + next_match.start()].strip()


def table_rows(section):
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if "---" in line or "指標" in line or "日本時間" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    return rows


def first_matching_line(text, prefix):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return ""


def collect_nested_bullets(lines, start_marker, max_items):
    items = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(start_marker):
            collecting = True
            continue
        if collecting and stripped.startswith("- ") and not line.startswith("  "):
            break
        if collecting and stripped.startswith("- "):
            items.append(stripped[2:].strip())
            if len(items) >= max_items:
                break
    return items


def report_dates(timestamp):
    generated = ""
    target_us = ""
    target_japan = ""

    generated_match = re.search(r"レポート生成日時:\s*([^|]+)", timestamp)
    target_us_match = re.search(r"米国セッション対象日:\s*([^|]+)", timestamp)
    target_japan_match = re.search(r"日本株セッション対象日:\s*([^|]+)", timestamp)

    if generated_match:
        generated = generated_match.group(1).strip()
    if target_us_match:
        target_us = target_us_match.group(1).strip()
    if target_japan_match:
        target_japan = target_japan_match.group(1).strip()

    return generated, target_us, target_japan


def trim_to_limit(parts, limit):
    kept = []
    for part in parts:
        candidate = "\n\n".join(kept + [part])
        if len(candidate) <= limit:
            kept.append(part)
    return "\n\n".join(kept)


def truncate_sentence(text, limit):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text

    best = ""
    for marker in ("。", "、", " "):
        pos = text.rfind(marker, 0, limit + 1)
        if pos > len(best):
            best = text[: pos + (1 if marker != " " else 0)].strip()
    return best or text[:limit].rstrip()


def build_summary(report):
    timestamp = ""
    for line in report.splitlines()[:8]:
        if "レポート生成日時" in line:
            timestamp = line.strip()
            break
    generated, target_us, target_japan = report_dates(timestamp)

    score_section = section_text(report, "0. 定量スコア一覧")
    score_rows = table_rows(score_section)
    selected_scores = []
    wanted = {
        "米国市場方向感",
        "日本株影響",
        "半導体株影響",
        "グロース株影響",
        "金融株影響",
        "為替影響（ドル円）",
        "本日のイベントリスク",
    }
    for cells in score_rows:
        if len(cells) >= 4 and cells[0] in wanted:
            comment = truncate_sentence(cells[3], SCORE_COMMENT_CHARS)
            selected_scores.append(f"- {cells[0]}: {cells[1]} / {cells[2]} - {comment}")

    summary_section = section_text(report, "1. 全体サマリー")
    summary_lines = summary_section.splitlines()
    theme = first_matching_line(summary_section, "- 本日の中心テーマ:")
    bull_items = collect_nested_bullets(summary_lines, "- 強気材料", 2)
    bear_items = collect_nested_bullets(summary_lines, "- 弱気材料", 2)

    event_section = section_text(report, "7. 本日の注目イベントスケジュール")
    event_lines = []
    for cells in table_rows(event_section)[:3]:
        if len(cells) >= 5:
            focus = truncate_sentence(cells[4], EVENT_FOCUS_CHARS)
            event_lines.append(f"- {cells[0]} {cells[1]}（{cells[2]}）: {focus}")

    closing_section = (
        section_text(report, "12. 結びの要約")
        or section_text_contains(report, "一言スタンス")
        or section_text_contains(report, "結び")
    )
    closing = first_matching_line(closing_section, "- ")
    if closing.startswith("- "):
        closing = closing[2:].strip()

    heading = "**朝の投資ニュースまとめ**"
    if generated:
        heading += f"\n作成: {generated}"
    else:
        posted_at = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M JST")
        heading += f"\n投稿: {posted_at}"
    if target_us or target_japan:
        heading += f"\n対象: 米国 {target_us or '-'} / 日本 {target_japan or '-'}"

    parts = [heading]
    if selected_scores:
        parts.append("**定量スコア**\n" + "\n".join(selected_scores))
    if theme:
        parts.append("**中心テーマ**\n" + theme.removeprefix("- ").strip())
    if bull_items:
        parts.append("**強気材料**\n" + "\n".join(f"- {truncate_sentence(item, MATERIAL_CHARS)}" for item in bull_items))
    if bear_items:
        parts.append("**弱気材料**\n" + "\n".join(f"- {truncate_sentence(item, MATERIAL_CHARS)}" for item in bear_items))
    if event_lines:
        parts.append("**本日の注目イベント**\n" + "\n".join(event_lines))
    if closing:
        parts.append("**一言スタンス**\n" + truncate_sentence(closing, CLOSING_CHARS))

    return trim_to_limit(parts, SUMMARY_MAX_CHARS)


def request_json(method, url, token, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "deep-research-discord-poster/1.0",
        },
    )

    while True:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code == 429:
                try:
                    retry_after = json.loads(body).get("retry_after", 1)
                except json.JSONDecodeError:
                    retry_after = 1
                time.sleep(float(retry_after) + 0.25)
                continue
            raise RuntimeError(f"Discord API error {error.code}: {body}") from error


def post_message(channel_id, token, content):
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    return request_json("POST", url, token, {"content": content})


def main():
    parser = argparse.ArgumentParser(
        description="Post a Markdown report to Discord using a bot token."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="agy-market-report/2026-05-31/report/morning_market_report.md",
        help="Markdown file to post.",
    )
    parser.add_argument(
        "--channel-id",
        default=os.environ.get("DISCORD_CHANNEL_ID"),
        help="Discord channel ID. Defaults to DISCORD_CHANNEL_ID.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("DISCORD_BOT_TOKEN"),
        help="Discord bot token. Defaults to DISCORD_BOT_TOKEN.",
    )
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=DEFAULT_CHUNK_CHARS,
        help=f"Maximum characters per message before part labels. Default: {DEFAULT_CHUNK_CHARS}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the number of messages that would be posted without calling Discord.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Post a concise Discord-friendly summary instead of the full report.",
    )
    args = parser.parse_args()

    if args.chunk_chars <= 0 or args.chunk_chars > MAX_DISCORD_CONTENT_CHARS - 80:
        parser.error("--chunk-chars must leave room for Discord's 2000 character message limit")

    with open(args.file, "r", encoding="utf-8") as report_file:
        report = report_file.read().strip()

    if args.summary:
        report = build_summary(report)

    chunks = split_message(report, args.chunk_chars)
    total = len(chunks)
    label = "Market Report Summary" if args.summary else "Market Report"
    if total == 1:
        labeled_chunks = chunks
    else:
        labeled_chunks = [
            f"**{label} ({index}/{total})**\n{chunk}"
            for index, chunk in enumerate(chunks, start=1)
        ]

    too_long = [len(chunk) for chunk in labeled_chunks if len(chunk) > MAX_DISCORD_CONTENT_CHARS]
    if too_long:
        raise SystemExit(f"Internal split error: message over Discord limit: {max(too_long)} chars")

    if args.dry_run:
        print(f"file={args.file}")
        print(f"messages={total}")
        print(f"max_message_chars={max(len(chunk) for chunk in labeled_chunks) if labeled_chunks else 0}")
        return

    if not args.token:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Export it or pass --token.")
    if not args.channel_id:
        raise SystemExit("DISCORD_CHANNEL_ID is not set. Export it or pass --channel-id.")

    for index, content in enumerate(labeled_chunks, start=1):
        response = post_message(args.channel_id, args.token, content)
        print(f"posted {index}/{total}: {response.get('id', '(no id returned)')}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()

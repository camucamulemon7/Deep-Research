#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Smoke-test stand-in for `opencode run`.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("message", nargs="*")
    run_parser.add_argument("--dir", required=True)
    run_parser.add_argument("--file", action="append", default=[])
    run_parser.add_argument("--title", default="")
    run_parser.add_argument("--model")
    run_parser.add_argument("--agent")
    run_parser.add_argument("--format")
    args, _unknown = parser.parse_known_args()

    if args.command != "run":
        raise SystemExit(f"Unsupported command: {args.command}")

    work_dir = Path(args.dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    prompt_names = [Path(prompt).name for prompt in args.file]

    if "prompt_improvement_points.md" in prompt_names:
        (work_dir / "prompt_improvement.md").write_text(
            "# Smoke improved prompt\n\nCreate the market report files requested by the workflow.\n",
            encoding="utf-8",
        )
        (work_dir / "next_day_evaluation_report.md").write_text(
            "# Smoke evaluation\n\nBackend smoke test completed.\n",
            encoding="utf-8",
        )
        (work_dir / "evaluation_score.json").write_text(
            json.dumps({"smoke_test": True}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return

    (work_dir / "morning_market_report.md").write_text(
        "\n".join(
            [
                "# 朝の投資ニュースまとめ",
                "",
                "レポート生成日時: smoke-test | 米国セッション対象日: smoke | 日本株セッション対象日: smoke",
                "",
                "## 0. 定量スコア一覧",
                "| 指標 | スコア | 判定 | コメント |",
                "| --- | --- | --- | --- |",
                "| 米国市場方向感 | 0 | 中立 | smoke test |",
                "",
                "## 1. 全体サマリー",
                "- 本日の中心テーマ: smoke test",
                "- 強気材料",
                "  - smoke test",
                "- 弱気材料",
                "  - smoke test",
                "",
                "## 7. 本日の注目イベントスケジュール",
                "| 日本時間 | イベント | 地域 | 重要度 | 注目点 |",
                "| --- | --- | --- | --- | --- |",
                "| 00:00 | smoke | test | low | smoke test |",
                "",
                "## 10. 出典・検証メモ",
                "- Smoke Source: https://example.com/smoke | 取得時刻: smoke-test",
                "",
                "## 12. 結びの要約",
                "- smoke test completed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (work_dir / "research_context.md").write_text(
        "# Smoke Research Context\n\n- source: https://example.com/smoke\n- fetched: smoke-test\n",
        encoding="utf-8",
    )
    (work_dir / "market_facts.json").write_text(
        json.dumps(
            {
                "as_of_jst": "smoke-test",
                "target_us_session_date": "smoke",
                "target_japan_session_date": "smoke",
                "market_data": {
                    "dow": {
                        "value": None,
                        "change": None,
                        "source_name": "Smoke Source",
                        "source_url": "https://example.com/smoke",
                        "as_of_jst": "smoke-test",
                        "confidence": "low",
                    }
                },
                "top_news": [
                    {
                        "title": "Smoke test",
                        "summary": "Smoke test news item.",
                        "source_name": "Smoke Source",
                        "source_url": "https://example.com/smoke",
                        "as_of_jst": "smoke-test",
                        "confidence": "low",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (work_dir / "market_thesis.md").write_text(
        "# Smoke Thesis\n\n- 中心テーマ: smoke test\n- 強気材料: smoke test\n- 弱気材料: smoke test\n",
        encoding="utf-8",
    )
    (work_dir / "market_score.json").write_text(
        json.dumps(
            {
                "scores": [
                    {
                        "name": "米国市場方向感",
                        "score": 0,
                        "confidence": "low",
                        "supporting_factors": ["smoke test"],
                        "opposing_factors": ["取得不可データあり"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (work_dir / "report_audit.md").write_text(
        "# Smoke Audit\n\n- source: checked\n- 日付: checked\n- 矛盾: none\n- 取得不可: noted\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

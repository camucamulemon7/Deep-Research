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
                "## 12. 結びの要約",
                "- smoke test completed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (work_dir / "market_score.json").write_text(
        json.dumps({"smoke_test": True}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

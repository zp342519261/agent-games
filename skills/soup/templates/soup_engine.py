#!/usr/bin/env python3
"""海龟汤引擎：锁定汤面/汤底、渲染 UI、记问答。无题库。Stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== SOUP_UI_BEGIN ==="
UI_END = "=== SOUP_UI_END ==="

STATE_DIR = Path(".soup")
STATE_PATH = STATE_DIR / "state.json"

THEMES = ("黑暗", "日常", "奇幻", "职场", "校园", "随机")
THEMES_RESOLVED = ("黑暗", "日常", "奇幻", "职场", "校园")
DIFFICULTIES = ("简单", "普通", "困难")
ANSWERS = ("是", "不是", "无关", "接近了")
SURFACE_MIN, SURFACE_MAX = 8, 200
TRUTH_MIN = 20


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def emit_ui(body: str) -> None:
    print(UI_BEGIN)
    print(body.rstrip("\n"))
    print(UI_END)


def default_state() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "status": "configuring",
        "theme": "随机",
        "difficulty": "普通",
        "theme_resolved": None,
        "surface": None,
        "truth": None,
        "qa": [],
        "outcome": None,
    }


def load_state() -> Optional[dict[str, Any]]:
    if not STATE_PATH.is_file():
        return None
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(st: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(st, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def theme_line(st: dict[str, Any]) -> str:
    t = st["theme"]
    r = st.get("theme_resolved")
    if st["status"] != "configuring" and r:
        if t == "随机":
            return f"主题：随机 → {r}"
        return f"主题：{r}"
    return f"主题：{t}"


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "海龟汤 · 配置",
        "",
        theme_line(st),
        f"难度：{st['difficulty']}",
        "",
        "主题：黑暗 / 日常 / 奇幻 / 职场 / 校园 / 随机",
        "难度：简单 / 普通 / 困难",
        "",
        "默认：主题随机、难度普通。确认后才编汤开局。",
        "改配置：set --theme T --difficulty D",
        "确认开始：由 Agent 编汤后 start",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def cmd_init(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        st = default_state()
        save_state(st)
        emit_ui(render_config(st))
        return
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    die("本局进行中，要用 next 才会回到配置")


def cmd_set(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置阶段改主题/难度（先 init）")
    if args.theme is not None:
        if args.theme not in THEMES:
            die(f"未知主题：{args.theme}")
        st["theme"] = args.theme
    if args.difficulty is not None:
        if args.difficulty not in DIFFICULTIES:
            die(f"未知难度：{args.difficulty}")
        st["difficulty"] = args.difficulty
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
海龟汤引擎 v{ENGINE_VERSION}
  init     进入/重绘配置（不编汤）
  set      --theme T --difficulty D
  start    --surface S --truth T --theme-resolved R
  info     查看当前 UI
  secret   仅 Agent：打印汤底（不要给用户看）
  log      --q 问题 --a 是|不是|无关|接近了
  reveal   --won 猜对揭底
  giveup   认输揭底
  next     回配置（保留主题/难度）
  help     本帮助

用户侧：
  /海龟汤  或  /海龟汤 init
  确认配置后再开始；局中直接提问
  /海龟汤 giveup  |  /海龟汤 next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="soup_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init")
    ini.set_defaults(func=cmd_init)

    st = sub.add_parser("set")
    st.add_argument("--theme", default=None)
    st.add_argument("--difficulty", default=None)
    st.set_defaults(func=cmd_set)

    hp = sub.add_parser("help")
    hp.set_defaults(func=cmd_help)

    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""修仙肉鸽引擎：状态机、校验、战斗、天劫、轮回、大纲。Stdlib only."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== XIUXIAN_UI_BEGIN ==="
UI_END = "=== XIUXIAN_UI_END ==="
STATE_DIR = Path(".xiuxian")
STATE_PATH = STATE_DIR / "state.json"

REALMS = ("炼气", "筑基", "金丹", "元婴", "化神")
THRESHOLDS = (0, 50, 120, 220, 350)
ROLES = ("SAFE", "GREEDY", "WEIRD")
DEATH_LABEL = {
    "combat": "恶斗",
    "accident": "意外",
    "backlash": "走火",
    "tribulation": "渡劫失败",
    "given_up": "自绝",
}


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def emit_ui(body: str) -> None:
    print(UI_BEGIN)
    print(body.rstrip("\n"))
    print(UI_END)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        die(message)


def default_meta() -> dict[str, Any]:
    return {
        "exp": 0,
        "realm": "炼气",
        "max_hp": 20,
        "atk": 3,
        "qi": 0,
        "inventory": [],
        "skills": [],
        "cycles": 0,
        "lives": [],
    }


def default_state() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "status": "hub",
        "meta": default_meta(),
        "run": None,
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


def require_state() -> dict[str, Any]:
    st = load_state()
    if st is None:
        die("先 init")
    return st


def slot_cap_from(cycles: int, pouch_n: int) -> int:
    return min(10, 4 + cycles + pouch_n)


def render_hub(st: dict[str, Any], notice: str = "") -> str:
    m = st["meta"]
    pouch = sum(s["n"] for s in m["skills"] if s["kind"] == "pouch")
    cap = slot_cap_from(m["cycles"], pouch)
    used = len(m["inventory"])
    lives = "无" if not m["lives"] else f"{len(m['lives'])} 世"
    lines = [
        "【轮回系统】系统空间",
        "",
        f"轮回次数：{m['cycles']}",
        f"境界：{m['realm']}  经验：{m['exp']}",
        f"气血上限：{m['max_hp']}  攻：{m['atk']}  灵气：{m['qi']}",
        f"死物：{used}/{cap}",
        f"功法：{len(m['skills'])}/3",
        f"前世：{lives}",
        "",
        "确认后 start 开启新一世。活物不会出现在这里。",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def cmd_init(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        st = default_state()
        save_state(st)
        emit_ui(render_hub(st))
        return
    if st["status"] == "hub":
        emit_ui(render_hub(st))
        return
    die("一世进行中或待轮回，不能 init 覆盖")


def cmd_help(_: argparse.Namespace) -> None:
    print(
        "\n".join(
            [
                "/修仙  短局修仙肉鸽",
                "命令：init start draft inscribe choose use log recall info giveup next help",
                "draft / help 无 UI 标记，不要把 draft 贴给用户。",
            ]
        )
    )


def cmd_stub(_: argparse.Namespace) -> None:
    die("未实现")


def build_parser() -> Parser:
    p = Parser(prog="xiuxian_engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("help").set_defaults(func=cmd_help)
    for name in (
        "start",
        "draft",
        "inscribe",
        "choose",
        "use",
        "log",
        "recall",
        "info",
        "giveup",
        "next",
    ):
        sub.add_parser(name).set_defaults(func=cmd_stub)
    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""修仙肉鸽引擎：状态机、校验、战斗、天劫、轮回、大纲。Stdlib only."""

from __future__ import annotations

import argparse
import json
import os
import random
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


def realm_index(realm: str) -> int:
    return REALMS.index(realm)


def next_realm(realm: str) -> Optional[str]:
    i = realm_index(realm)
    if i >= len(REALMS) - 1:
        return None
    return REALMS[i + 1]


def need_tribulation(meta: dict[str, Any], run_realm: str) -> bool:
    nxt = next_realm(run_realm)
    if nxt is None:
        return False
    return meta["exp"] >= THRESHOLDS[realm_index(nxt)]


def roll_slots(seed: int, floor: int) -> list[dict[str, str]]:
    roles = list(ROLES)
    random.Random(seed + floor).shuffle(roles)
    return [{"role": r} for r in roles]


def new_run(meta: dict[str, Any], seed: int) -> dict[str, Any]:
    return {
        "seed": seed,
        "floor": 1,
        "realm": meta["realm"],
        "hp": meta["max_hp"],
        "max_hp": meta["max_hp"],
        "atk": meta["atk"],
        "qi": meta["qi"],
        "inventory": [dict(x) for x in meta["inventory"]],
        "skills": [dict(x) for x in meta["skills"]],
        "allies": [],
        "trib_run": 0,
        "fight_mods": [],
        "qi_bonus": 0,
        "dawn": 0,
        "luck_floor": 0,
        "danger_used": False,
        "revive_used": False,
        "node_type": "event",
        "slots": [],
        "choices": None,
        "body": None,
        "outline": None,
        "chronicle": [],
        "pending_log": False,
        "death_cause": None,
        "next_p": 1,
        "next_s": 1,
        "next_a": 1,
        "last_fight": None,
        "scavenged": False,
        "did_battle": False,
        "won_battle": False,
    }


def apply_enter_passives(run: dict[str, Any]) -> None:
    for sk in run["skills"]:
        if sk["kind"] == "breath":
            run["hp"] = min(run["max_hp"], run["hp"] + sk["n"])
        elif sk["kind"] == "qi_flow":
            cap = 99 + sum(s["n"] for s in run["skills"] if s["kind"] == "meridians") + run["qi_bonus"]
            run["qi"] = min(cap, run["qi"] + sk["n"])


def enter_floor(st: dict[str, Any]) -> None:
    run = st["run"]
    run["dawn"] = 0
    run["luck_floor"] = 0
    run["fight_mods"] = []
    run["scavenged"] = False
    run["did_battle"] = False
    run["won_battle"] = False
    run["last_fight"] = None
    run["choices"] = None
    run["body"] = None
    run["outline"] = None
    apply_enter_passives(run)
    if need_tribulation(st["meta"], run["realm"]):
        run["node_type"] = "tribulation"
        run["slots"] = []
    elif run["floor"] % 2 == 1:
        run["node_type"] = "event"
        run["slots"] = roll_slots(run["seed"], run["floor"])
    else:
        run["node_type"] = "event_battle"
        run["slots"] = roll_slots(run["seed"], run["floor"])


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


def cmd_start(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "hub":
        die("只能在系统空间 start（ended 须先 next）")
    seed = args.seed
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "big")
    st["run"] = new_run(st["meta"], int(seed))
    enter_floor(st)
    st["status"] = "composing"
    save_state(st)
    emit_ui(
        "\n".join(
            [
                f"【轮回系统】第{st['meta']['cycles'] + 1}世",
                f"境界：{st['run']['realm']}",
                f"第{st['run']['floor']}层 · 待落墨",
            ]
        )
    )


def cmd_draft(_: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "composing":
        die("只能在 composing 时 draft")
    run = st["run"]
    lines = [
        f"floor={run['floor']}",
        f"node_type={run['node_type']}",
        f"realm={run['realm']}",
        f"hp={run['hp']}/{run['max_hp']} atk={run['atk']} qi={run['qi']}",
        f"exp={st['meta']['exp']}",
        f"inventory={json.dumps(run['inventory'], ensure_ascii=False)}",
        f"skills={json.dumps(run['skills'], ensure_ascii=False)}",
        f"allies={json.dumps(run['allies'], ensure_ascii=False)}",
        f"slots={json.dumps(run['slots'], ensure_ascii=False)}",
        f"chronicle_tail={json.dumps(run['chronicle'][-3:], ensure_ascii=False)}",
        f"prev_digest={st['meta']['lives'][-1]['digest'] if st['meta']['lives'] else ''}",
    ]
    print("\n".join(lines))


def build_parser() -> Parser:
    p = Parser(prog="xiuxian_engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("help").set_defaults(func=cmd_help)
    sp = sub.add_parser("start")
    sp.add_argument("--seed", type=int, default=None)
    sp.set_defaults(func=cmd_start)
    sub.add_parser("draft").set_defaults(func=cmd_draft)
    for name in (
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

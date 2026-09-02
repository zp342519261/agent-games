#!/usr/bin/env python3
"""修仙肉鸽引擎：状态机、校验、战斗、天劫、轮回、大纲。Stdlib only."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
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
ITEM_TYPES = {
    "dan": "丹药", "fu": "符箓", "qi": "法器", "cai": "灵材",
    "jian": "兵刃", "jia": "甲胄", "zhu": "宝珠", "yin": "印玺",
    "jing": "宝镜", "zhong": "钟鼎", "fan": "灵幡", "ling": "令牌",
    "yu": "玉简", "tu": "舆图", "jiu": "灵酒", "xiang": "香烛",
    "huan": "戒环", "pei": "玉佩", "gu": "枯骨", "ping": "瓶罐",
    "zhen": "阵盘", "shi": "灵石", "lu": "丹炉", "nang": "香囊",
    "du": "毒剂", "cha": "灵茶", "zhou": "咒片", "xue": "凝血",
    "ta": "宝塔", "deng": "长明灯", "shu": "残页", "suo": "锁链",
    "wei": "帷幔", "guan": "冠冕", "dai": "束带", "pao": "道袍",
}


def _fx(ui: str, lo: int, hi: int, passive: bool = False) -> dict[str, Any]:
    return {"ui": ui, "n": (lo, hi), "passive": passive}


FX = {
    "revive": _fx("续命", 1, 1, True),
    "hp": _fx("回气", 4, 12),
    "qi": _fx("补灵", 1, 5),
    "atk": _fx("增攻", 1, 3),
    "maxhp": _fx("炼体", 2, 6),
    "spark": _fx("走火", 2, 6),
    "fullhp": _fx("回满", 1, 1),
    "exp": _fx("顿悟", 3, 10),
    "luck_floor": _fx("避凶", 5, 15),
    "meridians_now": _fx("通脉", 2, 10),
    "trib": _fx("祭天", 5, 15),
    "dawn_fight": _fx("壮行", 1, 2),
    "ward": _fx("避战", 1, 1),
    "skip": _fx("遁走", 1, 1),
    "mirror": _fx("金蝉", 1, 1),
    "bomb": _fx("破军", 1, 1),
    "iron": _fx("铁衣", 1, 1),
    "second": _fx("连击", 1, 1),
    "barrier": _fx("护盾", 2, 8),
    "weaken": _fx("破甲", 2, 6),
    "poison": _fx("淬毒", 1, 2),
    "haste": _fx("连斩", 1, 1),
    "freeze": _fx("冰封", 1, 1),
    "slow": _fx("滞空", 1, 2),
    "drain_fight": _fx("噬血", 1, 1),
    "reflect_fight": _fx("反噬", 1, 2),
    "thunder_fight": _fx("雷引", 1, 3),
    "step_fight": _fx("身法", 1, 1),
    "pack_fight": _fx("御兽", 1, 2),
    "frenzy_fight": _fx("狂化", 1, 3),
    "guard_fight": _fx("护体", 1, 1),
    "double_exp": _fx("双倍", 1, 1),
    "sight": _fx("天眼", 1, 1),
    "rest": _fx("调息", 4, 8),
    "bait": _fx("挑衅", 1, 1),
    "qi_fight": _fx("抽灵", 1, 1),
    "vigor_fight": _fx("气盛", 1, 2),
    "execute_fight": _fx("斩杀", 1, 3),
    "insight_now": _fx("开悟", 1, 3),
    "last_stand_fight": _fx("残息", 1, 1),
    "blood_price_fight": _fx("燃血", 1, 3),
}


def _skill(ui: str, lo: int, hi: int) -> dict[str, Any]:
    return {"ui": ui, "n": (lo, hi)}


SKILLS = {
    "breath": _skill("吐纳", 1, 3),
    "qi_flow": _skill("聚灵", 1, 2),
    "meditation": _skill("入定", 1, 3),
    "meridians": _skill("经脉", 2, 10),
    "regen": _skill("战愈", 1, 2),
    "leech_qi": _skill("抽灵", 1, 1),
    "dawn": _skill("晨曦", 1, 2),
    "spark_ward": _skill("避火", 1, 4),
    "sword": _skill("攻伐", 1, 2),
    "thunder": _skill("雷引", 1, 3),
    "drain": _skill("噬血", 1, 1),
    "reflect": _skill("反噬", 1, 2),
    "frenzy": _skill("狂化", 1, 3),
    "vigor": _skill("气盛", 1, 2),
    "execute": _skill("斩杀", 1, 3),
    "poison": _skill("淬毒", 1, 2),
    "haste": _skill("连斩", 1, 1),
    "blood_price": _skill("燃血", 1, 3),
    "weaken": _skill("破甲", 2, 6),
    "pack": _skill("御兽", 1, 2),
    "guard": _skill("护体", 1, 1),
    "step": _skill("身法", 1, 1),
    "slow": _skill("滞空", 1, 2),
    "freeze": _skill("冰封", 1, 1),
    "barrier": _skill("护盾", 2, 8),
    "dusk": _skill("夜行", 1, 1),
    "last_stand": _skill("残息", 1, 1),
    "brother": _skill("结义", 1, 1),
    "insight": _skill("悟性", 1, 2),
    "hunt": _skill("猎魔", 2, 5),
    "sage": _skill("苦修", 1, 3),
    "scavenger": _skill("拾荒", 1, 3),
    "will": _skill("道心", 5, 15),
    "brute": _skill("霸体", 5, 15),
    "shell_heart": _skill("金钟", 5, 15),
    "tranquil": _skill("镇心", 5, 15),
    "luck": _skill("气运", 5, 15),
    "danger": _skill("危机", 1, 1),
    "oath": _skill("双修", 2, 6),
    "pouch": _skill("扩容", 1, 1),
    "memory": _skill("残忆", 1, 1),
    "vessel": _skill("道器", 1, 1),
}

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


def validate_outline(outline: str) -> str:
    outline = outline.strip()
    if not 20 <= len(outline) <= 80:
        raise ValueError("outline 长度须为 20～80")
    return outline


def _new_effect() -> dict[str, Any]:
    return {
        "hp": 0,
        "atk": 0,
        "qi": 0,
        "maxhp": 0,
        "battle": False,
        "accident": 0,
        "grant": None,
        "ally": None,
        "skill": None,
    }


def _checked_name(name: str) -> str:
    if not 2 <= len(name) <= 8:
        raise ValueError("名字长度须为 2～8")
    return name


def _checked_n(n_text: str, bounds: tuple[int, int], label: str) -> int:
    n = int(n_text)
    if not bounds[0] <= n <= bounds[1]:
        raise ValueError(f"{label} n 超出范围")
    return n


def parse_effect(text: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        raise ValueError("效果不能为空")
    parsed = _new_effect()
    seen: set[str] = set()
    reward_kind: Optional[str] = None

    for atom in compact.split(";"):
        if not atom:
            raise ValueError("效果包含空原子")
        numeric = re.fullmatch(r"(hp|atk|qi)([+-])(\d+)", atom)
        if numeric:
            key, sign, amount = numeric.groups()
            if key in seen:
                raise ValueError(f"{key} 只能出现一次")
            seen.add(key)
            value = int(amount)
            if value <= 0:
                raise ValueError("属性变化必须大于 0")
            parsed[key] = value if sign == "+" else -value
            continue
        maxhp = re.fullmatch(r"maxhp\+(\d+)", atom)
        if maxhp:
            if "maxhp" in seen:
                raise ValueError("maxhp 只能出现一次")
            seen.add("maxhp")
            parsed["maxhp"] = int(maxhp.group(1))
            if parsed["maxhp"] <= 0:
                raise ValueError("maxhp 变化必须大于 0")
            continue
        if atom == "battle":
            if "battle" in seen:
                raise ValueError("battle 只能出现一次")
            seen.add("battle")
            parsed["battle"] = True
            continue
        accident = re.fullmatch(r"accident:p=(\d+)", atom)
        if accident:
            if "accident" in seen:
                raise ValueError("accident 只能出现一次")
            seen.add("accident")
            parsed["accident"] = _checked_n(accident.group(1), (5, 40), "accident")
            continue
        grant = re.fullmatch(
            r"grant:type=([^:;]+):fx=([^:;]+):n=(\d+):name=([^:;]+)",
            atom,
        )
        if grant:
            if reward_kind is not None:
                raise ValueError("grant/ally/skill 不能同时出现")
            item_type, fx, n_text, name = grant.groups()
            if item_type not in ITEM_TYPES or fx not in FX:
                raise ValueError("未知道具类型或效果")
            parsed["grant"] = {
                "type": item_type,
                "fx": fx,
                "n": _checked_n(n_text, FX[fx]["n"], fx),
                "name": _checked_name(name),
            }
            reward_kind = "grant"
            continue
        ally = re.fullmatch(
            r"ally:bond=([^:;]+):n=(\d+):name=([^:;]+)",
            atom,
        )
        if ally:
            if reward_kind is not None:
                raise ValueError("grant/ally/skill 不能同时出现")
            bond, n_text, name = ally.groups()
            if bond not in {"partner", "dao", "beast"}:
                raise ValueError("未知同行关系")
            parsed["ally"] = {
                "bond": bond,
                "n": _checked_n(n_text, (1, 3), "ally"),
                "name": _checked_name(name),
            }
            reward_kind = "ally"
            continue
        skill = re.fullmatch(
            r"skill:kind=([^:;]+):n=(\d+):name=([^:;]+)",
            atom,
        )
        if skill:
            if reward_kind is not None:
                raise ValueError("grant/ally/skill 不能同时出现")
            kind, n_text, name = skill.groups()
            if kind not in SKILLS:
                raise ValueError("未知功法")
            parsed["skill"] = {
                "kind": kind,
                "n": _checked_n(n_text, SKILLS[kind]["n"], kind),
                "name": _checked_name(name),
            }
            reward_kind = "skill"
            continue
        raise ValueError(f"非法效果原子：{atom}")
    return parsed


SAFE_GRANT_FX = {
    "hp", "qi", "maxhp", "ward", "iron", "luck_floor", "exp", "fullhp",
    "barrier", "meridians_now", "dawn_fight", "sight", "rest", "insight_now",
}
SAFE_SKILLS = {
    "breath", "qi_flow", "guard", "meditation", "meridians", "sage", "dawn",
    "spark_ward",
}
GREEDY_GRANT_FX = {
    "atk", "spark", "bomb", "second", "weaken", "poison", "haste",
    "frenzy_fight", "drain_fight", "thunder_fight", "pack_fight", "ward",
    "mirror", "bait", "blood_price_fight", "execute_fight", "vigor_fight",
}
GREEDY_SKILLS = {
    "sword", "thunder", "drain", "hunt", "frenzy", "vigor", "execute",
    "poison", "haste", "blood_price", "weaken", "leech_qi",
}


def validate_effect(role: str, parsed: dict[str, Any], node_type: str) -> None:
    if role not in ROLES:
        raise ValueError("未知选项角色")
    if node_type not in {"event", "event_battle"}:
        raise ValueError("非事件层不能提交普通效果")
    grant, ally, skill = parsed["grant"], parsed["ally"], parsed["skill"]
    if role == "SAFE":
        if parsed["battle"] or parsed["hp"] < 0 or parsed["accident"] or parsed["atk"] > 1:
            raise ValueError("SAFE 含风险或攻过高")
        if grant and grant["fx"] not in SAFE_GRANT_FX:
            raise ValueError("SAFE 道具效果不合法")
        if ally and (ally["bond"] != "partner" or ally["n"] != 1):
            raise ValueError("SAFE 同行不合法")
        if skill and skill["kind"] not in SAFE_SKILLS:
            raise ValueError("SAFE 功法不合法")
        if not (
            parsed["hp"] > 0
            or parsed["qi"] > 0
            or parsed["maxhp"] > 0
            or grant
            or ally
            or skill
        ):
            raise ValueError("SAFE 至少须有一项有效收益")
    elif role == "GREEDY":
        if not 0 < parsed["atk"] <= 3:
            raise ValueError("GREEDY 必须合法增加攻击")
        if not (parsed["battle"] or parsed["hp"] <= -3 or parsed["accident"]):
            raise ValueError("GREEDY 必须有风险")
        if grant and grant["fx"] not in GREEDY_GRANT_FX:
            raise ValueError("GREEDY 道具效果不合法")
        if ally and (ally["bond"] != "beast" or not 1 <= ally["n"] <= 3):
            raise ValueError("GREEDY 同行不合法")
        if skill and skill["kind"] not in GREEDY_SKILLS:
            raise ValueError("GREEDY 功法不合法")
    else:
        if parsed["atk"] > 2:
            raise ValueError("WEIRD 攻击收益过高")
        if not (
            parsed["qi"] != 0
            or grant
            or ally
            or skill
            or parsed["maxhp"] > 0
            or (parsed["hp"] < 0 and parsed["qi"] > 0)
        ):
            raise ValueError("WEIRD 缺少异质效果")


def fmt_effect(parsed: dict[str, Any]) -> str:
    lines = []
    labels = {"hp": "气血", "atk": "攻", "qi": "灵气", "maxhp": "气血上限"}
    for key in ("hp", "atk", "qi", "maxhp"):
        value = parsed[key]
        if value:
            lines.append(f"{labels[key]}{value:+d}")
    if parsed["battle"]:
        lines.append("随后恶斗")
    if parsed["accident"]:
        lines.append(f"意外p={parsed['accident']}")
    if parsed["grant"]:
        item = parsed["grant"]
        detail = {
            "hp": f"气血+{item['n']}",
            "qi": f"灵气+{item['n']}",
            "atk": f"攻+{item['n']}",
            "maxhp": f"气血上限+{item['n']}",
        }.get(item["fx"], f"{FX[item['fx']]['ui']} n={item['n']}")
        lines.append(
            f"获得：{item['name']}[{ITEM_TYPES[item['type']]}/{FX[item['fx']]['ui']}] {detail}"
        )
    if parsed["ally"]:
        ally = parsed["ally"]
        bond_ui = {"partner": "伙伴", "dao": "道侣", "beast": "灵兽"}
        lines.append(f"同行：{ally['name']}（{bond_ui[ally['bond']]}）")
    if parsed["skill"]:
        skill = parsed["skill"]
        lines.append(f"功法：{skill['name']}[{SKILLS[skill['kind']]['ui']}]")
    return "；".join(lines)


def trib_chances(run: dict[str, Any]) -> tuple[int, int, int]:
    def skill_n(kind: str) -> int:
        return sum(skill["n"] for skill in run["skills"] if skill["kind"] == kind)

    dao_count = sum(1 for ally in run["allies"] if ally["bond"] == "dao")
    base = run["trib_run"] + skill_n("will") + skill_n("oath") * dao_count

    def clamp(value: int) -> int:
        return max(5, min(95, value))

    hard = clamp(run["atk"] * 4 + run["qi"] * 2 + base + skill_n("brute"))
    guard = clamp(
        run["hp"] * 40 // run["max_hp"]
        + run["qi"] * 2
        + base
        + skill_n("shell_heart")
    )
    heart = clamp(run["qi"] * 3 + base + skill_n("tranquil"))
    return hard, guard, heart


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


def qi_cap(run: dict[str, Any]) -> int:
    meridians = sum(
        skill["n"] for skill in run["skills"] if skill["kind"] == "meridians"
    )
    return 99 + meridians + run["qi_bonus"]


def apply_enter_passives(run: dict[str, Any]) -> None:
    for sk in run["skills"]:
        if sk["kind"] == "breath":
            run["hp"] = min(run["max_hp"], run["hp"] + sk["n"])
        elif sk["kind"] == "qi_flow":
            run["qi"] = min(qi_cap(run), run["qi"] + sk["n"])


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


def cmd_inscribe(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "composing":
        die("只能在 composing 时 inscribe")
    run = st["run"]
    try:
        outline = validate_outline(args.outline)
        body = args.body.strip()
        option_texts = [args.c1.strip(), args.c2.strip(), args.c3.strip()]
        if not body or not all(option_texts):
            raise ValueError("正文和三个选项均不能为空")

        if run["node_type"] == "tribulation":
            if any(effect is not None for effect in (args.e1, args.e2, args.e3)):
                raise ValueError("天劫层不能提交 --e*")
            tribs = ("hard", "guard", "heart")
            choices = []
            for text, trib in zip(option_texts, tribs):
                parsed = _new_effect()
                parsed["trib"] = trib
                choices.append(
                    {"text": text, "effect": f"trib:{trib}", "role": "TRIB", "parsed": parsed}
                )
            chances = trib_chances(run)
            effect_lines = [
                f"{i}. {choice['text']}｜成功率 {chance}%"
                for i, (choice, chance) in enumerate(zip(choices, chances), 1)
            ]
        else:
            effects = (args.e1, args.e2, args.e3)
            if any(effect is None for effect in effects):
                raise ValueError("非天劫层必须提交三个 --e*")
            choices = []
            effect_lines = []
            for i, (text, effect, slot) in enumerate(
                zip(option_texts, effects, run["slots"]),
                1,
            ):
                parsed = parse_effect(effect)
                validate_effect(slot["role"], parsed, run["node_type"])
                choices.append(
                    {
                        "text": text,
                        "effect": effect,
                        "role": slot["role"],
                        "parsed": parsed,
                    }
                )
                effect_lines.append(
                    f"{i}. {text}｜{slot['role']}｜{fmt_effect(parsed)}"
                )
    except ValueError as exc:
        die(str(exc))

    run["outline"] = outline
    run["body"] = body
    run["choices"] = choices
    st["status"] = "choosing"
    save_state(st)
    emit_ui("\n".join([body, "", *effect_lines]))


def apply_parsed(st: dict[str, Any], parsed: dict[str, Any], act: str) -> None:
    run = st["run"]
    run["max_hp"] += parsed["maxhp"]
    run["hp"] = max(0, min(run["max_hp"], run["hp"] + parsed["hp"]))
    run["atk"] = max(1, run["atk"] + parsed["atk"])
    run["qi"] = max(0, min(qi_cap(run), run["qi"] + parsed["qi"]))

    for key, prefix, counter, target in (
        ("grant", "p", "next_p", "inventory"),
        ("ally", "a", "next_a", "allies"),
        ("skill", "s", "next_s", "skills"),
    ):
        reward = parsed[key]
        if reward is None:
            continue
        entry = {"uid": f"{prefix}{run[counter]}", **reward}
        run[counter] += 1
        run[target].append(entry)

    if parsed["battle"]:
        run["did_battle"] = True
    if run["hp"] == 0:
        run["death_cause"] = "backlash"


def append_chronicle(st: dict[str, Any], act: str, facts: dict[str, Any]) -> None:
    run = st["run"]
    run["chronicle"].append(
        {
            "floor": run["floor"],
            "node": run["node_type"],
            "realm": run["realm"],
            "setup": run["outline"],
            "act": act,
            "facts": facts,
            "after": None,
        }
    )
    run["chronicle"] = run["chronicle"][-40:]
    run["pending_log"] = True


def advance_or_end(st: dict[str, Any]) -> None:
    run = st["run"]
    if run["hp"] <= 0:
        st["status"] = "ended"
        return
    run["floor"] += 1
    enter_floor(st)
    st["status"] = "composing"


def _skill_total(run: dict[str, Any], kind: str) -> int:
    return sum(skill["n"] for skill in run["skills"] if skill["kind"] == kind)


def _render_choice_result(
    run: dict[str, Any],
    choice: dict[str, Any],
    gained: Optional[dict[str, Any]],
) -> str:
    lines = [
        f"已选择：{choice['text']}",
        f"结算：{fmt_effect(choice['parsed']) or '无属性变化'}",
        f"气血：{run['hp']}/{run['max_hp']}  攻：{run['atk']}  灵气：{run['qi']}",
    ]
    if gained is not None:
        lines.append(f"获得：{gained['name']}（{gained['uid']}）")
    if run["hp"] <= 0:
        lines.append(f"此世终结：{DEATH_LABEL[run['death_cause']]}")
    else:
        lines.append(f"进入第{run['floor'] + 1}层")
    return "\n".join(lines)


def cmd_choose(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "choosing":
        die("只能在 choosing 时 choose")
    run = st["run"]
    choice = run["choices"][args.n - 1]
    parsed = choice["parsed"]
    run["did_battle"] = parsed["battle"] or run["node_type"] == "event_battle"

    before_counts = {
        "inventory": len(run["inventory"]),
        "allies": len(run["allies"]),
        "skills": len(run["skills"]),
    }
    apply_parsed(st, parsed, f"choose:{args.n}")
    gained = None
    for target in ("inventory", "allies", "skills"):
        if len(run[target]) > before_counts[target]:
            gained = run[target][-1]
            break

    facts = {
        "effect": choice["effect"],
        "hp": run["hp"],
        "max_hp": run["max_hp"],
        "atk": run["atk"],
        "qi": run["qi"],
        "gained": gained,
        "did_battle": run["did_battle"],
    }
    result_ui = _render_choice_result(run, choice, gained)
    append_chronicle(st, f"choose:{args.n}", facts)

    if run["hp"] > 0:
        layer_exp = 5 + _skill_total(run, "insight")
        if not run["did_battle"]:
            layer_exp += _skill_total(run, "sage")
        st["meta"]["exp"] += layer_exp
    advance_or_end(st)
    save_state(st)
    emit_ui(result_ui)


def _render_choosing(st: dict[str, Any]) -> str:
    run = st["run"]
    effect_lines = [
        f"{i}. {choice['text']}｜{choice['role']}｜{fmt_effect(choice['parsed'])}"
        for i, choice in enumerate(run["choices"], 1)
    ]
    return "\n".join([run["body"], "", *effect_lines])


def _render_ended(st: dict[str, Any]) -> str:
    run = st["run"]
    cause = DEATH_LABEL.get(run["death_cause"], "未知")
    return "\n".join(
        [
            "【轮回系统】此世已终",
            f"境界：{run['realm']}  层数：{run['floor']}",
            f"死因：{cause}",
        ]
    )


def cmd_info(_: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] == "hub":
        body = render_hub(st)
    elif st["status"] == "choosing":
        body = _render_choosing(st)
    elif st["status"] == "ended":
        body = _render_ended(st)
    else:
        die("composing 时请先 draft 并完成落墨")
    emit_ui(body)


def build_parser() -> Parser:
    p = Parser(prog="xiuxian_engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("help").set_defaults(func=cmd_help)
    sp = sub.add_parser("start")
    sp.add_argument("--seed", type=int, default=None)
    sp.set_defaults(func=cmd_start)
    sub.add_parser("draft").set_defaults(func=cmd_draft)
    ins = sub.add_parser("inscribe")
    ins.add_argument("--outline", default="")
    ins.add_argument("--body", default="")
    ins.add_argument("--c1", default="")
    ins.add_argument("--c2", default="")
    ins.add_argument("--c3", default="")
    ins.add_argument("--e1", default=None)
    ins.add_argument("--e2", default=None)
    ins.add_argument("--e3", default=None)
    ins.set_defaults(func=cmd_inscribe)
    choose = sub.add_parser("choose")
    choose.add_argument("--n", type=int, choices=(1, 2, 3), required=True)
    choose.set_defaults(func=cmd_choose)
    sub.add_parser("info").set_defaults(func=cmd_info)
    for name in (
        "use",
        "log",
        "recall",
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

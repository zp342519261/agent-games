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


def _rebirth_selection(
    entries: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ranked = sorted(
        entries,
        key=lambda entry: (-entry["n"], -int(entry["uid"][1:])),
    )
    kept = sorted(ranked[:limit], key=lambda entry: int(entry["uid"][1:]))
    dropped = sorted(ranked[limit:], key=lambda entry: int(entry["uid"][1:]))
    return kept, dropped


def preview_rebirth(st: dict[str, Any]) -> dict[str, Any]:
    run = st["run"]
    meta = st["meta"]
    skills = run["skills"]
    skill_kinds = {skill["kind"] for skill in skills}
    pouch_n = sum(skill["n"] for skill in skills if skill["kind"] == "pouch")
    slot_cap = slot_cap_from(meta["cycles"], pouch_n)
    kept_items, dropped_items = _rebirth_selection(run["inventory"], slot_cap)
    kept_skills, dropped_skills = _rebirth_selection(skills, 3)

    exp = meta["exp"] * (8 if "memory" in skill_kinds else 7) // 10
    attr_rate = 9 if "vessel" in skill_kinds else 8
    max_hp = max(20, run["max_hp"] * attr_rate // 10)
    atk = max(3, run["atk"] * attr_rate // 10)
    qi = run["qi"] * attr_rate // 10
    realm_i = realm_index(run["realm"])
    while realm_i > 0 and exp < THRESHOLDS[realm_i]:
        realm_i -= 1
    realm = REALMS[realm_i]

    return {
        "slot_cap": slot_cap,
        "kept_items": kept_items,
        "dropped_items": dropped_items,
        "kept_skills": kept_skills,
        "dropped_skills": dropped_skills,
        "exp": exp,
        "realm": realm,
        "max_hp": max_hp,
        "atk": atk,
        "qi": qi,
    }


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


def validate_body(body: str) -> str:
    body = body.strip()
    if not 20 <= len(body) <= 400:
        raise ValueError("body 长度须为 20～400")
    return body


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


def trib_roll(seed: int, floor: int) -> int:
    return random.Random(seed + 90001 + floor).randint(1, 100)


def need_tribulation(meta: dict[str, Any], run_realm: str) -> bool:
    nxt = next_realm(run_realm)
    if nxt is None:
        return False
    return meta["exp"] >= THRESHOLDS[realm_index(nxt)]


def roll_slots(seed: int, floor: int) -> list[dict[str, str]]:
    roles = list(ROLES)
    random.Random(seed + floor).shuffle(roles)
    return [{"role": r} for r in roles]


def _next_uid(entries: list[dict[str, Any]]) -> int:
    return max((int(entry["uid"][1:]) for entry in entries), default=0) + 1


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
        "chronicle_trimmed": False,
        "pending_log": False,
        "death_cause": None,
        "next_p": _next_uid(meta["inventory"]),
        "next_s": _next_uid(meta["skills"]),
        "next_a": 1,
        "last_fight": None,
        "scavenged": False,
        "did_battle": False,
        "won_battle": False,
        "travel_looted": False,
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
        *[f"- {life['digest']}" for life in m["lives"]],
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
    ensure_after(st)
    save_state(st)
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
    if run["node_type"] == "tribulation":
        hard, guard, heart = trib_chances(run)
        lines.extend(
            [
                f"hard={hard}",
                f"guard={guard}",
                f"heart={heart}",
            ]
        )
    print("\n".join(lines))


def cmd_inscribe(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "composing":
        die("只能在 composing 时 inscribe")
    run = st["run"]
    try:
        if args.mode not in ("travel", "fork"):
            raise ValueError("必须指定 --mode travel 或 fork")
        outline = validate_outline(args.outline)
        body = validate_body(args.body)
        if run["node_type"] == "tribulation" and args.mode == "travel":
            raise ValueError("天劫必须定夺，不能游历")
        if args.mode == "travel":
            if any(x.strip() for x in (args.c1, args.c2, args.c3)):
                raise ValueError("游历不能带 --c*")
            if any(effect is not None for effect in (args.e1, args.e2, args.e3)):
                raise ValueError("游历不能带 --e*")
            if args.gain is not None:
                raise ValueError("游历收获尚未接线")
        if args.gain is not None:
            raise ValueError("定夺不能带 --gain")
        if args.mode == "travel":
            ensure_after(st)
            run["outline"] = outline
            run["body"] = body
            settle_travel(st, None)
            save_state(st)
            emit_ui(body)
            return
        option_texts = [args.c1.strip(), args.c2.strip(), args.c3.strip()]
        if not all(option_texts):
            raise ValueError("三个选项均不能为空")

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
            effect_lines = [
                f"{i}. {choice['text']}"
                for i, choice in enumerate(choices, 1)
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
                    f"{i}. {text}"
                )
    except ValueError as exc:
        die(str(exc))

    ensure_after(st)
    run["outline"] = outline
    run["body"] = body
    run["choices"] = choices
    st["status"] = "choosing"
    save_state(st)
    emit_ui("\n".join([body, "", *effect_lines]))


def settle_travel(
    st: dict[str, Any],
    parsed: Optional[dict[str, Any]],
) -> None:
    run = st["run"]
    gained = None
    if parsed is not None:
        before = {
            "inventory": len(run["inventory"]),
            "allies": len(run["allies"]),
            "skills": len(run["skills"]),
        }
        apply_parsed(st, parsed, "travel+gain")
        for target in ("inventory", "allies", "skills"):
            if len(run[target]) > before[target]:
                gained = run[target][-1]
                break
        act = "travel+gain"
        effect_label = "gain"
    else:
        act = "travel"
        effect_label = "travel"
    _apply_floor_end_passives(run)
    facts = _facts_text(run, effect_label, gained, None)
    append_chronicle(st, act, facts)
    _award_floor_exp(st)
    run["travel_looted"] = parsed is not None
    advance_or_end(st)


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


def resolve_accident(run: dict[str, Any], probability: int) -> bool:
    if probability <= 0:
        return False
    luck = _skill_total(run, "luck") + run["luck_floor"]
    has_sight = any(mod["fx"] == "sight" for mod in run["fight_mods"])
    effective_probability = 0 if has_sight else max(0, probability - luck)
    roll = random.Random(
        run["seed"] + 80000 + run["floor"]
    ).randint(1, 100)
    if roll > effective_probability:
        return False
    if _skill_total(run, "danger") and not run["danger_used"]:
        run["danger_used"] = True
        return False
    run["death_cause"] = "accident"
    return True


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
    if len(run["chronicle"]) > 40:
        run["chronicle_trimmed"] = True
    run["chronicle"] = run["chronicle"][-40:]
    run["pending_log"] = True


def mechanical_after(entry: dict[str, Any], run_snapshot: dict[str, Any]) -> str:
    act = entry["act"]
    if act.startswith("choose:"):
        act_label = f"选{act.split(':', 1)[1]}"
    elif act.startswith("use:"):
        act_label = f"用{act.split(':', 1)[1]}"
    elif act == "giveup":
        act_label = "自绝"
    else:
        act_label = act

    facts = str(entry.get("facts", ""))
    battle = "战胜" if "战胜" in facts else "战败" if "战败" in facts else "未战"
    destination = "身死" if run_snapshot.get("death_cause") else "下层"
    return (
        f"{act_label}；气血{run_snapshot['hp']}/{run_snapshot['max_hp']}；"
        f"{battle}；{destination}"
    )


def ensure_after(st: dict[str, Any]) -> None:
    run = st.get("run")
    if not run or not run.get("pending_log"):
        return
    if not run["chronicle"]:
        run["pending_log"] = False
        return
    run["chronicle"][-1]["after"] = mechanical_after(run["chronicle"][-1], run)
    run["pending_log"] = False


def advance_or_end(st: dict[str, Any]) -> None:
    run = st["run"]
    if run["death_cause"] is not None:
        st["status"] = "ended"
        return
    run["floor"] += 1
    enter_floor(st)
    st["status"] = "composing"


def _skill_total(run: dict[str, Any], kind: str) -> int:
    return sum(skill["n"] for skill in run["skills"] if skill["kind"] == kind)


def enemy_stats(floor: int, realm: str) -> tuple[int, int]:
    capped_floor = min(floor, 40)
    index = realm_index(realm)
    return 8 + 2 * capped_floor + 4 * index, 2 + capped_floor // 2 + index


def _fight_mod_total(run: dict[str, Any], *effects: str) -> int:
    wanted = set(effects)
    return sum(mod["n"] for mod in run["fight_mods"] if mod["fx"] in wanted)


def _combat_total(run: dict[str, Any], skill: str, *effects: str) -> int:
    return _skill_total(run, skill) + _fight_mod_total(run, *effects)


def _trigger(
    triggered: list[str],
    run: dict[str, Any],
    skill: Optional[str] = None,
    *effects: str,
) -> None:
    if skill is not None and _skill_total(run, skill):
        name = SKILLS[skill]["ui"]
        if name not in triggered:
            triggered.append(name)
    wanted = set(effects)
    for mod in run["fight_mods"]:
        if mod["fx"] in wanted:
            name = FX[mod["fx"]]["ui"]
            if name not in triggered:
                triggered.append(name)


def _consume_revive(run: dict[str, Any]) -> bool:
    if run["revive_used"]:
        return False
    for index, item in enumerate(run["inventory"]):
        if item["fx"] == "revive":
            del run["inventory"][index]
            run["revive_used"] = True
            return True
    return False


def fight(st: dict[str, Any]) -> dict[str, Any]:
    run = st["run"]
    enemy_hp, enemy_atk = enemy_stats(run["floor"], run["realm"])
    enemy_hp = max(1, enemy_hp - _combat_total(run, "weaken", "weaken"))
    bomb = _fight_mod_total(run, "bomb")
    if bomb:
        enemy_hp = max(1, enemy_hp // 2)

    barrier = _combat_total(run, "barrier", "barrier")
    poison = _combat_total(run, "poison", "poison")
    pack = _combat_total(run, "pack", "pack_fight")
    slow = _combat_total(run, "slow", "slow")
    guard = _combat_total(run, "guard", "guard_fight")
    drain = _combat_total(run, "drain", "drain_fight")
    reflect = _combat_total(run, "reflect", "reflect_fight")
    thunder = _combat_total(run, "thunder", "thunder_fight")
    frenzy = _combat_total(run, "frenzy", "frenzy_fight")
    vigor = _combat_total(run, "vigor", "vigor_fight")
    execute = _combat_total(run, "execute", "execute_fight")
    blood_price = _combat_total(run, "blood_price", "blood_price_fight")
    last_stand = _combat_total(run, "last_stand", "last_stand_fight")
    extra_hit = bool(
        _skill_total(run, "haste")
        or _fight_mod_total(run, "second", "haste")
    )
    brother = _skill_total(run, "brother")
    partner = sum(
        ally["n"] + brother
        for ally in run["allies"]
        if ally["bond"] == "partner"
    )
    dao = sum(a["n"] for a in run["allies"] if a["bond"] == "dao")
    beasts = [a["n"] for a in run["allies"] if a["bond"] == "beast"]
    iron = _fight_mod_total(run, "iron")

    log = [f"开战：敌 气血{enemy_hp} 攻{enemy_atk}"]
    triggered: list[str] = []
    if _combat_total(run, "weaken", "weaken"):
        _trigger(triggered, run, "weaken", "weaken")
    if bomb:
        _trigger(triggered, run, None, "bomb")
    if _combat_total(run, "step", "step_fight"):
        _trigger(triggered, run, "step", "step_fight")
    player_strikes = 0
    enemy_strikes = 0
    last_stand_used = False

    def survive_lethal() -> bool:
        nonlocal last_stand_used
        if run["hp"] > 0:
            return True
        if _consume_revive(run):
            run["hp"] = 1
            if "续命" not in triggered:
                triggered.append("续命")
            return True
        if last_stand and not last_stand_used:
            run["hp"] = 1
            last_stand_used = True
            _trigger(triggered, run, "last_stand", "last_stand_fight")
            return True
        return False

    def player_hit(round_no: int, with_thunder: bool) -> None:
        nonlocal enemy_hp, player_strikes
        if blood_price:
            run["hp"] -= 1
            _trigger(triggered, run, "blood_price", "blood_price_fight")
            if not survive_lethal():
                return
        bonus = random.Random(
            run["seed"] + 1000 * run["floor"] + player_strikes
        ).randint(0, 1)
        dawn = run["dawn"] + _skill_total(run, "dawn")
        sword = _skill_total(run, "sword")
        damage = run["atk"] + dawn + bonus + partner + sword
        if dawn:
            _trigger(triggered, run, "dawn", "dawn_fight")
        if sword:
            _trigger(triggered, run, "sword")
        if brother and partner:
            _trigger(triggered, run, "brother")
        if frenzy and run["hp"] * 2 <= run["max_hp"]:
            damage += frenzy
            _trigger(triggered, run, "frenzy", "frenzy_fight")
        if vigor and run["hp"] * 2 >= run["max_hp"]:
            damage += vigor
            _trigger(triggered, run, "vigor", "vigor_fight")
        if execute and enemy_hp <= 4 * execute:
            damage += execute
            _trigger(triggered, run, "execute", "execute_fight")
        if blood_price:
            damage += blood_price
        if with_thunder and thunder:
            damage += thunder
            _trigger(triggered, run, "thunder", "thunder_fight")
        enemy_hp -= damage
        player_strikes += 1
        log.append(f"第{round_no}轮 你造成{damage}伤害")
        if drain:
            run["hp"] = min(run["max_hp"], run["hp"] + drain)
            _trigger(triggered, run, "drain", "drain_fight")
        leech = _skill_total(run, "leech_qi") + _fight_mod_total(run, "qi_fight")
        if leech:
            run["qi"] = min(qi_cap(run), run["qi"] + leech)
            _trigger(triggered, run, "leech_qi", "qi_fight")

    for round_no in range(1, 41):
        regen = _skill_total(run, "regen")
        if regen:
            run["hp"] = min(run["max_hp"], run["hp"] + regen)
            _trigger(triggered, run, "regen")
        if dao:
            run["hp"] = min(run["max_hp"], run["hp"] + dao)
        if poison and round_no >= 2:
            enemy_hp -= poison
            _trigger(triggered, run, "poison", "poison")
        if enemy_hp <= 0:
            break

        for beast in beasts:
            damage = beast + pack
            enemy_hp -= damage
            log.append(f"第{round_no}轮 灵兽造成{damage}伤害")
            if pack:
                _trigger(triggered, run, "pack", "pack_fight")
            if enemy_hp <= 0:
                break
        if enemy_hp <= 0:
            break

        player_hit(round_no, player_strikes == 0)
        if run["hp"] <= 0 or enemy_hp <= 0:
            break
        if extra_hit:
            _trigger(triggered, run, "haste", "second", "haste")
            player_hit(round_no, False)
            if run["hp"] <= 0 or enemy_hp <= 0:
                break

        enemy_strikes += 1
        damage = max(1, enemy_atk - slow)
        dodged = (
            (enemy_strikes == 1 and _combat_total(run, "step", "step_fight"))
            or (enemy_strikes % 2 == 0 and _combat_total(run, "freeze", "freeze"))
        )
        if dodged:
            damage = 0
            if enemy_strikes == 1:
                _trigger(triggered, run, "step", "step_fight")
            else:
                _trigger(triggered, run, "freeze", "freeze")
        else:
            if slow:
                _trigger(triggered, run, "slow", "slow")
            reduction = iron + guard
            if run["floor"] % 2 == 0:
                reduction += _skill_total(run, "dusk")
                _trigger(triggered, run, "dusk")
            damage = max(0, damage - reduction)
            if iron:
                _trigger(triggered, run, None, "iron")
            if guard:
                _trigger(triggered, run, "guard", "guard_fight")

        absorbed = min(barrier, damage)
        barrier -= absorbed
        hp_damage = damage - absorbed
        if absorbed:
            _trigger(triggered, run, "barrier", "barrier")
        run["hp"] -= hp_damage
        log.append(f"第{round_no}轮 敌造成{hp_damage}伤害")
        if hp_damage and reflect:
            enemy_hp -= reflect
            _trigger(triggered, run, "reflect", "reflect_fight")
        if not survive_lethal() or enemy_hp <= 0:
            break

    won = enemy_hp <= 0 and run["hp"] > 0
    if not won:
        run["hp"] = 0
        run["death_cause"] = "combat"
    run["did_battle"] = True
    run["won_battle"] = won
    log.append("战胜" if won else "战败")
    report = {"log": log, "won": won, "triggered": triggered}
    run["last_fight"] = report
    return report


def should_fight(
    node_type: str,
    parsed: dict[str, Any],
    mods: list[dict[str, Any]],
) -> bool:
    effects = {mod["fx"] for mod in mods}
    if effects & {"ward", "skip", "mirror", "rest"}:
        return False
    return node_type == "event_battle" or parsed["battle"] or "bait" in effects


def _facts_text(
    run: dict[str, Any],
    effect: str,
    gained: Optional[dict[str, Any]],
    report: Optional[dict[str, Any]],
) -> str:
    parts = [
        effect,
        f"气血{run['hp']}/{run['max_hp']} 攻{run['atk']} 灵气{run['qi']}",
    ]
    if gained is not None:
        parts.append(f"获得{gained['name']}")
    if report is not None:
        parts.extend(("开战", "战胜" if report["won"] else "战败"))
        parts.extend(report["triggered"])
    return "；".join(part for part in parts if part)


def _award_floor_exp(st: dict[str, Any]) -> None:
    run = st["run"]
    if run["death_cause"] is not None:
        return
    layer_exp = 5 + _skill_total(run, "insight")
    layer_exp += _fight_mod_total(run, "insight_now")
    if not run["did_battle"]:
        layer_exp += _skill_total(run, "sage")
    if run["won_battle"]:
        layer_exp += 5 + _skill_total(run, "hunt")
    used_effects = {mod["fx"] for mod in run["fight_mods"]}
    if used_effects & {"ward", "skip", "mirror"}:
        layer_exp += _skill_total(run, "scavenger")
    if _fight_mod_total(run, "double_exp"):
        layer_exp *= 2
    st["meta"]["exp"] += layer_exp


def _apply_floor_end_passives(run: dict[str, Any]) -> None:
    if run["death_cause"] is None and not run["did_battle"]:
        run["hp"] = min(
            run["max_hp"],
            run["hp"] + _skill_total(run, "meditation"),
        )


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
    if run["death_cause"] is not None:
        lines.append(f"此世终结：{DEATH_LABEL[run['death_cause']]}")
    else:
        lines.append(f"进入第{run['floor'] + 1}层")
    return "\n".join(lines)


def resolve_trib(st: dict[str, Any], n: int) -> bool:
    run = st["run"]
    chance = trib_chances(run)[n - 1]
    if trib_roll(run["seed"], run["floor"]) > chance:
        run["death_cause"] = "tribulation"
        return False

    realm = next_realm(run["realm"])
    if realm is None:
        raise ValueError("化神境无须渡劫")
    run["realm"] = realm
    st["meta"]["realm"] = realm
    return True


def cmd_choose(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "choosing":
        die("只能在 choosing 时 choose")
    run = st["run"]
    choice = run["choices"][args.n - 1]
    parsed = choice["parsed"]
    if run["node_type"] == "tribulation":
        resolve_trib(st, args.n)
        _apply_floor_end_passives(run)
        facts = _facts_text(run, choice["effect"], None, None)
        result_ui = _render_choice_result(run, choice, None)
        append_chronicle(st, f"choose:{args.n}", facts)
        _award_floor_exp(st)
        advance_or_end(st)
        save_state(st)
        emit_ui(result_ui)
        return

    before_counts = {
        "inventory": len(run["inventory"]),
        "allies": len(run["allies"]),
        "skills": len(run["skills"]),
    }
    apply_parsed(st, parsed, f"choose:{args.n}")
    if run["death_cause"] is None:
        resolve_accident(run, parsed["accident"])
    report = fight(st) if run["death_cause"] is None and should_fight(
        run["node_type"], parsed, run["fight_mods"]
    ) else None
    _apply_floor_end_passives(run)
    gained = None
    for target in ("inventory", "allies", "skills"):
        if len(run[target]) > before_counts[target]:
            gained = run[target][-1]
            break

    facts = _facts_text(run, choice["effect"], gained, report)
    result_ui = _render_choice_result(run, choice, gained)
    append_chronicle(st, f"choose:{args.n}", facts)

    _award_floor_exp(st)
    advance_or_end(st)
    save_state(st)
    emit_ui(result_ui)


def _apply_item(st: dict[str, Any], item: dict[str, Any]) -> None:
    run = st["run"]
    fx, n = item["fx"], item["n"]
    if fx == "hp":
        run["hp"] = min(run["max_hp"], run["hp"] + n)
    elif fx == "qi":
        run["qi"] = min(qi_cap(run), run["qi"] + n)
    elif fx == "atk":
        run["atk"] += n
    elif fx == "maxhp":
        run["max_hp"] += n
        run["hp"] += n
    elif fx == "fullhp":
        run["hp"] = run["max_hp"]
    elif fx == "exp":
        st["meta"]["exp"] += n
    elif fx == "luck_floor":
        run["luck_floor"] += n
    elif fx == "meridians_now":
        run["qi_bonus"] += n
        run["qi"] = min(qi_cap(run), run["qi"] + n)
    elif fx == "trib":
        run["trib_run"] = min(20, run["trib_run"] + n)
    elif fx == "dawn_fight":
        run["dawn"] += n
        run["fight_mods"].append(dict(item))
    elif fx == "spark":
        ward = _skill_total(run, "spark_ward")
        run["qi"] = min(qi_cap(run), run["qi"] + n)
        run["hp"] = max(0, run["hp"] - max(0, 3 - ward))
    elif fx == "mirror":
        ward = _skill_total(run, "spark_ward")
        run["hp"] = max(0, run["hp"] - max(0, 4 - ward))
        run["fight_mods"].append(dict(item))
    elif fx == "rest":
        run["hp"] = min(run["max_hp"], run["hp"] + n)
        run["fight_mods"].append(dict(item))
    else:
        run["fight_mods"].append(dict(item))
    if run["hp"] <= 0:
        run["death_cause"] = "backlash"


def cmd_use(args: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "choosing":
        die("只能在 choosing 时 use")
    run = st["run"]
    if run["node_type"] == "tribulation":
        die("天劫层不能 use")
    item = next((x for x in run["inventory"] if x["uid"] == args.id), None)
    if item is None:
        die("未知死物 id")
    if item["fx"] == "revive":
        die("续命死物不能主动 use")

    run["inventory"].remove(item)
    _apply_item(st, item)
    empty = _new_effect()
    report = fight(st) if run["hp"] > 0 and should_fight(
        run["node_type"], empty, run["fight_mods"]
    ) else None
    _apply_floor_end_passives(run)
    facts = _facts_text(run, f"use:{item['uid']}:{item['name']}", None, report)
    append_chronicle(st, f"use:{item['uid']}", facts)
    _award_floor_exp(st)
    result_ui = "\n".join(
        [
            f"已使用：{item['name']}（{item['uid']}）",
            f"气血：{run['hp']}/{run['max_hp']}  攻：{run['atk']}  灵气：{run['qi']}",
            (
                f"此世终结：{DEATH_LABEL[run['death_cause']]}"
                if run["hp"] <= 0
                else f"进入第{run['floor'] + 1}层"
            ),
        ]
    )
    advance_or_end(st)
    save_state(st)
    emit_ui(result_ui)


def _render_choosing(st: dict[str, Any]) -> str:
    run = st["run"]
    effect_lines = [
        f"{i}. {choice['text']}"
        for i, choice in enumerate(run["choices"], 1)
    ]
    return "\n".join([run["body"], "", *effect_lines])


def _rebirth_names(entries: list[dict[str, Any]]) -> str:
    return "、".join(entry["name"] for entry in entries) or "无"


def _render_rebirth(st: dict[str, Any], preview: dict[str, Any]) -> str:
    allies = st["run"]["allies"]
    return "\n".join(
        [
            f"带走死物：{_rebirth_names(preview['kept_items'])}",
            f"遗弃死物：{_rebirth_names(preview['dropped_items'])}",
            f"带走功法：{_rebirth_names(preview['kept_skills'])}",
            f"遗弃功法：{_rebirth_names(preview['dropped_skills'])}",
            f"活物未随轮回：{_rebirth_names(allies)}",
            (
                f"轮回后：{preview['realm']} 经验{preview['exp']} "
                f"气血上限{preview['max_hp']} 攻{preview['atk']} 灵气{preview['qi']}"
            ),
        ]
    )


def _render_ended(st: dict[str, Any]) -> str:
    run = st["run"]
    cause = DEATH_LABEL.get(run["death_cause"], "未知")
    rebirth = _render_rebirth(st, preview_rebirth(st))
    return "\n".join(
        [
            "【轮回系统】此世已终",
            f"境界：{run['realm']}  层数：{run['floor']}",
            f"死因：{cause}",
            "",
            "待轮回：",
            rebirth,
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


def cmd_log(args: argparse.Namespace) -> None:
    st = require_state()
    run = st.get("run")
    if not run or not run.get("pending_log") or not run["chronicle"]:
        die("当前没有待补写的经历")
    after = args.after.strip()
    if not 20 <= len(after) <= 80:
        die("after 长度须为 20～80")
    run["chronicle"][-1]["after"] = after
    run["pending_log"] = False
    save_state(st)
    print("经历已补写")


def _render_chronicle(
    entries: list[dict[str, Any]],
    trimmed: bool = False,
) -> str:
    lines = []
    if trimmed or len(entries) > 40:
        lines.append("（仅显示最近 40 条，较早经历已截断）")
    for entry in entries[-40:]:
        lines.extend(
            [
                f"第{entry['floor']}层 · {entry['realm']}",
                f"起：{entry['setup'] or '无'}",
                f"行：{entry['act']}｜{entry['facts']}",
                f"后：{entry['after'] or '待补写'}",
            ]
        )
    return "\n".join(lines) if lines else "暂无经历"


def cmd_recall(_: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] == "hub":
        lives = st["meta"]["lives"]
        body = "\n".join(
            ["【轮回系统】前世录"]
            + ([life["digest"] for life in lives] if lives else ["暂无前世"])
        )
    else:
        body = "\n".join(
            [
                f"【轮回系统】第{st['meta']['cycles'] + 1}世经历",
                _render_chronicle(
                    st["run"]["chronicle"],
                    st["run"].get("chronicle_trimmed", False),
                ),
            ]
        )
    emit_ui(body)


def cmd_giveup(_: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] not in {"composing", "choosing"}:
        die("只能在 composing 或 choosing 时 giveup")
    ensure_after(st)
    run = st["run"]
    run["death_cause"] = "given_up"
    append_chronicle(st, "giveup", "自绝")
    st["status"] = "ended"
    save_state(st)
    emit_ui(_render_ended(st))


def cmd_next(_: argparse.Namespace) -> None:
    st = require_state()
    if st["status"] != "ended":
        die("只能在 ended 时 next")

    ensure_after(st)
    run = st["run"]
    meta = st["meta"]
    cause = DEATH_LABEL.get(run["death_cause"], "未知")
    last_after = run["chronicle"][-1]["after"] if run["chronicle"] else ""
    digest = (
        f"第{meta['cycles'] + 1}世 · {run['realm']} · "
        f"历{run['floor']}层 · 死于{cause}"
    )
    if last_after:
        digest += f" · {last_after[:20]}"
    meta["lives"].append(
        {
            "cycle": meta["cycles"],
            "death_cause": run["death_cause"],
            "realm": run["realm"],
            "floors": run["floor"],
            "digest": digest,
            "entries": [dict(entry) for entry in run["chronicle"][-15:]],
        }
    )
    meta["lives"] = meta["lives"][-8:]
    preview = preview_rebirth(st)
    notice = "\n".join(["轮回完成：", _render_rebirth(st, preview)])
    meta.update(
        {
            "inventory": preview["kept_items"],
            "skills": preview["kept_skills"],
            "exp": preview["exp"],
            "realm": preview["realm"],
            "max_hp": preview["max_hp"],
            "atk": preview["atk"],
            "qi": preview["qi"],
        }
    )
    meta.pop("allies", None)
    meta["cycles"] += 1
    st["run"] = None
    st["status"] = "hub"
    save_state(st)
    emit_ui(render_hub(st, notice))


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
    ins.add_argument("--mode", default=None, choices=("travel", "fork"))
    ins.add_argument("--gain", default=None)
    ins.set_defaults(func=cmd_inscribe)
    choose = sub.add_parser("choose")
    choose.add_argument("--n", type=int, choices=(1, 2, 3), required=True)
    choose.set_defaults(func=cmd_choose)
    use = sub.add_parser("use")
    use.add_argument("--id", required=True)
    use.set_defaults(func=cmd_use)
    log = sub.add_parser("log")
    log.add_argument("--after", required=True)
    log.set_defaults(func=cmd_log)
    sub.add_parser("recall").set_defaults(func=cmd_recall)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("giveup").set_defaults(func=cmd_giveup)
    sub.add_parser("next").set_defaults(func=cmd_next)
    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

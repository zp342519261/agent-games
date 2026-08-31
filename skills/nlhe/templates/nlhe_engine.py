#!/usr/bin/env python3
"""NLHE engine: system RNG shuffle + JSON state. Stdlib only."""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_ENGINE_DIR = Path(__file__).resolve().parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

# 与 ~/.cursor/skills/nlhe/VERSION 保持一致；发版时两边一起改
ENGINE_VERSION = "1.5.2"

# Agent 必须原样展示此区间内的 stdout，禁止自行重绘 UI
UI_BEGIN = "=== NLHE_UI_BEGIN ==="
UI_END = "=== NLHE_UI_END ==="
SKILLS_LOCK_PATH = Path.home() / ".agents" / ".skill-lock.json"
SKILL_NAME = "nlhe"


def resolve_skill_root() -> Path:
    """Locate skill package: templates/ sibling, cwd/nlhe, or legacy ~/.cursor/skills/nlhe."""
    here = Path(__file__).resolve()
    if here.parent.name == "templates":
        candidate = here.parent.parent
        if (candidate / "VERSION").is_file():
            return candidate
    cwd_nlhe = Path.cwd() / "nlhe"
    if (cwd_nlhe / "VERSION").is_file():
        return cwd_nlhe.resolve()
    legacy = Path.home() / ".cursor" / "skills" / "nlhe"
    if (legacy / "VERSION").is_file():
        return legacy
    return cwd_nlhe.resolve()


SKILL_ROOT = resolve_skill_root()
SKILL_TEMPLATE = SKILL_ROOT / "templates" / "nlhe_engine.py"
SKILL_VERSION_FILE = SKILL_ROOT / "VERSION"

RANKS = "23456789TJQKA"
SUITS = "cdhs"
SUIT_SYM = {"c": "♣", "d": "♦", "h": "♥", "s": "♠"}
RANK_VAL = {r: i for i, r in enumerate(RANKS, start=2)}

STATE_DIR = Path(".nlhe")
STATE_PATH = STATE_DIR / "state.json"
LOCAL_VERSION_PATH = STATE_DIR / "VERSION"
ENGINE_PATH = Path(__file__).resolve()


class ActionError(Exception):
    pass


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_semver(text: str) -> tuple[int, ...]:
    text = text.strip().split("-")[0]
    parts = []
    for p in text.split("."):
        if not p.isdigit():
            break
        parts.append(int(p))
    return tuple(parts) if parts else (0,)


def read_skill_version() -> Optional[str]:
    if SKILL_VERSION_FILE.is_file():
        return SKILL_VERSION_FILE.read_text(encoding="utf-8").strip()
    if SKILL_TEMPLATE.is_file():
        # 兜底：从模板源码读 ENGINE_VERSION
        for line in SKILL_TEMPLATE.read_text(encoding="utf-8").splitlines():
            if line.startswith("ENGINE_VERSION"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


def read_local_marker_version() -> Optional[str]:
    if LOCAL_VERSION_PATH.is_file():
        return LOCAL_VERSION_PATH.read_text(encoding="utf-8").strip()
    return None


def write_local_marker(version: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_VERSION_PATH.write_text(version.strip() + "\n", encoding="utf-8")


def needs_upgrade() -> tuple[bool, str, str]:
    """返回 (需要升级, 本地版本, skill 版本)。"""
    skill_v = read_skill_version() or "0.0.0"
    local_v = ENGINE_VERSION
    marker = read_local_marker_version()
    if marker and parse_semver(marker) > parse_semver(local_v):
        # 标记比当前脚本新：脚本可能没拷全
        local_v = marker
    outdated = parse_semver(local_v) < parse_semver(skill_v)
    return outdated, local_v, skill_v



def card_str(c: str) -> str:
    return f"{c[0]}{SUIT_SYM[c[1]]}"


def cards_str(cards: list[str]) -> str:
    return " ".join(card_str(c) for c in cards) if cards else "—"


def replay_add(state: dict[str, Any], event: dict[str, Any]) -> None:
    state.setdefault("replay", []).append(event)


def player_tag(p: dict[str, Any]) -> str:
    label = p.get("style_label") or ""
    if p.get("is_human"):
        return f"{p['name']}"
    return f"{p['name']}({label})" if label else p["name"]


def format_action_line(state: dict[str, Any], seat: int, action: str, amount: Optional[int]) -> str:
    p = state["players"][seat]
    who = player_tag(p)
    if action == "fold" and p.get("is_human"):
        return f"{who} fold → 进入观战"
    if action == "raise" and amount is not None:
        return f"{who} raise→{amount}"
    if action == "allin":
        return f"{who} all-in"
    return f"{who} {action}"


def new_deck(rng: random.Random) -> list[str]:
    deck = [r + s for r in RANKS for s in SUITS]
    rng.shuffle(deck)
    return deck


def make_rng(seed: Optional[int]) -> random.Random:
    if seed is None:
        return random.SystemRandom()
    return random.Random(seed)


# ── hand evaluation (best 5 of 7) ───────────────────────────────────────────


def _eval5(cards: list[str]) -> tuple:
    vals = sorted((RANK_VAL[c[0]] for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    flush = len(set(suits)) == 1
    uniq = sorted(set(vals), reverse=True)
    straight_high = 0
    if len(uniq) == 5:
        if uniq[0] - uniq[4] == 4:
            straight_high = uniq[0]
        elif uniq == [14, 5, 4, 3, 2]:
            straight_high = 5
    counts: dict[int, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    by_count = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    quads = [v for v, n in by_count if n == 4]
    trips = [v for v, n in by_count if n == 3]
    pairs = [v for v, n in by_count if n == 2]
    kickers = sorted(counts.keys(), reverse=True)

    if flush and straight_high:
        return (8, straight_high)
    if quads:
        q = quads[0]
        k = max(v for v in kickers if v != q)
        return (7, q, k)
    if trips and (pairs or len(trips) > 1):
        t = trips[0]
        p = pairs[0] if pairs else trips[1]
        return (6, t, p)
    if flush:
        return (5, *sorted(vals, reverse=True))
    if straight_high:
        return (4, straight_high)
    if trips:
        t = trips[0]
        ks = [v for v in kickers if v != t][:2]
        return (3, t, *ks)
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        k = max(v for v in kickers if v != p1 and v != p2)
        return (2, p1, p2, k)
    if len(pairs) == 1:
        p = pairs[0]
        ks = [v for v in kickers if v != p][:3]
        return (1, p, *ks)
    return (0, *sorted(vals, reverse=True))


def best_hand(hole: list[str], board: list[str]) -> tuple:
    """最佳牌型。翻前仅 2 张时返回对子/高牌；翻后用 5 张组合。"""
    cards = [c for c in (hole + board) if c]
    if len(cards) < 2:
        return (0, 0)
    if len(cards) < 5:
        return _eval_short(cards)
    from itertools import combinations

    best: Optional[tuple] = None
    for combo in combinations(cards, 5):
        score = _eval5(list(combo))
        if best is None or score > best:
            best = score
    assert best is not None
    return best


def _eval_short(cards: list[str]) -> tuple:
    """不足 5 张时的粗评（翻前 / 极少见边角）。"""
    vals = sorted((RANK_VAL[c[0]] for c in cards), reverse=True)
    counts: dict[int, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    by_count = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    if by_count[0][1] >= 2:
        pair = by_count[0][0]
        ks = [v for v in vals if v != pair]
        return (1, pair, *ks[:3])
    return (0, *vals)


HAND_NAMES = {
    8: "同花顺",
    7: "四条",
    6: "葫芦",
    5: "同花",
    4: "顺子",
    3: "三条",
    2: "两对",
    1: "一对",
    0: "高牌",
}

RANK_CHAR = {
    14: "A",
    13: "K",
    12: "Q",
    11: "J",
    10: "T",
    9: "9",
    8: "8",
    7: "7",
    6: "6",
    5: "5",
    4: "4",
    3: "3",
    2: "2",
}


def describe_hand(score: tuple) -> str:
    """可读牌型，如 一对·A / 两对·K&7 / 皇家同花顺。"""
    if not score:
        return "—"
    cat = int(score[0])
    def rc(v: int) -> str:
        return RANK_CHAR.get(int(v), str(v))

    if cat == 8:
        return "皇家同花顺" if int(score[1]) == 14 else f"同花顺·{rc(score[1])}"
    if cat == 7:
        return f"四条·{rc(score[1])}"
    if cat == 6:
        return f"葫芦·{rc(score[1])}满{rc(score[2])}"
    if cat == 5:
        return f"同花·{rc(score[1])}高"
    if cat == 4:
        return f"顺子·{rc(score[1])}高"
    if cat == 3:
        return f"三条·{rc(score[1])}"
    if cat == 2:
        return f"两对·{rc(score[1])}&{rc(score[2])}"
    if cat == 1:
        return f"一对·{rc(score[1])}"
    return f"高牌·{rc(score[1])}" if len(score) > 1 else "高牌"


# ── state helpers ───────────────────────────────────────────────────────────


def default_name(i: int, human_ids: set[int]) -> str:
    return "You" if i in human_ids else f"Bot{i}"


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        die("无状态文件。请先 /NLHE init 查看配置，再 /NLHE init --start 开局")
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["engine_version"] = ENGINE_VERSION
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_local_marker(ENGINE_VERSION)


def in_hand(p: dict[str, Any]) -> bool:
    return not p["folded"]


def can_act(p: dict[str, Any]) -> bool:
    return not p["folded"] and not p["all_in"] and p["stack"] > 0


def max_bet(state: dict[str, Any]) -> int:
    return max((p["bet"] for p in state["players"] if in_hand(p)), default=0)


def seats_to_act(state: dict[str, Any]) -> list[int]:
    """Players who still need to match max_bet or haven't acted this street."""
    mb = max_bet(state)
    out = []
    for p in state["players"]:
        if not can_act(p):
            continue
        if p["bet"] < mb or not p.get("acted"):
            out.append(p["id"])
    return out


def next_from(state: dict[str, Any], start: int) -> Optional[int]:
    n = len(state["players"])
    need = set(seats_to_act(state))
    if not need:
        return None
    for k in range(1, n + 1):
        i = (start + k) % n
        if i in need:
            return i
    return None


def first_to_act_postflop(state: dict[str, Any]) -> Optional[int]:
    return next_from(state, state["button"])


def living(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in state["players"] if in_hand(p)]


# ── pots (side pots) ────────────────────────────────────────────────────────


@dataclass
class Pot:
    amount: int
    eligible: list[int]


def build_pots(state: dict[str, Any]) -> list[Pot]:
    """Distribute all committed chips (bets already moved? We track street bets
    in player.bet and pot has previous streets. At showdown, combine contrib."""
    # Use total contribution this hand stored in contrib
    contrib = {p["id"]: p.get("contrib", 0) for p in state["players"]}
    levels = sorted(set(c for c in contrib.values() if c > 0))
    pots: list[Pot] = []
    prev = 0
    for level in levels:
        layer = level - prev
        if layer <= 0:
            continue
        elig = [pid for pid, c in contrib.items() if c >= level]
        # only non-folded for winning; folded still contributed
        amount = layer * len(elig)
        winners_elig = [
            pid
            for pid in elig
            if not state["players"][pid]["folded"]
        ]
        pots.append(Pot(amount=amount, eligible=winners_elig or elig))
        prev = level
    return pots


def move_bets_to_pot(state: dict[str, Any]) -> None:
    for p in state["players"]:
        if p["bet"]:
            state["pot"] += p["bet"]
            p["contrib"] = p.get("contrib", 0) + p["bet"]
            p["bet"] = 0


# ── betting actions ─────────────────────────────────────────────────────────


def min_raise_to(state: dict[str, Any]) -> int:
    mb = max_bet(state)
    last = state.get("last_raise_size") or state["bb"]
    return mb + last


def apply_action(state: dict[str, Any], pid: int, action: str, amount: Optional[int]) -> None:
    p = state["players"][pid]
    if state.get("to_act") != pid:
        raise ActionError(f"现在不是座位 {pid} 行动")
    if not can_act(p):
        raise ActionError("该座位无法行动")

    action = action.lower()
    mb = max_bet(state)

    if action == "fold":
        p["folded"] = True
        p["acted"] = True
        if p.get("is_human"):
            state["watching"] = True
    elif action == "check":
        if p["bet"] < mb:
            raise ActionError("当前不能 check，请 call / raise / fold")
        p["acted"] = True
    elif action == "call":
        need = mb - p["bet"]
        if need <= 0:
            p["acted"] = True
        else:
            pay = min(need, p["stack"])
            p["stack"] -= pay
            p["bet"] += pay
            if p["stack"] == 0:
                p["all_in"] = True
            p["acted"] = True
    elif action == "raise":
        if amount is None:
            raise ActionError("raise 需要目标金额：raise <n>")
        target = amount
        mrt = min_raise_to(state)
        if target < mrt and target < p["bet"] + p["stack"]:
            raise ActionError(f"加注至少到 {mrt}（或 allin）")
        if target <= mb and target < p["bet"] + p["stack"]:
            raise ActionError(f"加注目标须大于当前最高注 {mb}")
        max_to = p["bet"] + p["stack"]
        target = min(target, max_to)
        pay = target - p["bet"]
        if pay <= 0:
            raise ActionError("无效加注")
        raise_size = target - mb
        p["stack"] -= pay
        p["bet"] = target
        if p["stack"] == 0:
            p["all_in"] = True
        if target > mb:
            state["last_raise_size"] = max(
                raise_size, state.get("last_raise_size") or state["bb"]
            )
            for q in state["players"]:
                if q["id"] != pid and can_act(q):
                    q["acted"] = False
        p["acted"] = True
    elif action == "allin":
        pay = p["stack"]
        if pay <= 0:
            raise ActionError("没有筹码")
        new_bet = p["bet"] + pay
        if new_bet > mb:
            raise_size = new_bet - mb
            state["last_raise_size"] = max(
                raise_size, state.get("last_raise_size") or state["bb"]
            )
            for q in state["players"]:
                if q["id"] != pid and can_act(q):
                    q["acted"] = False
        p["bet"] = new_bet
        p["stack"] = 0
        p["all_in"] = True
        p["acted"] = True
    else:
        raise ActionError(f"未知行动: {action}")

    state["history"].append(
        {"seat": pid, "action": action, "amount": amount, "street": state["street"]}
    )
    replay_add(
        state,
        {
            "type": "act",
            "street": state["street"],
            "seat": pid,
            "action": action,
            "amount": amount,
            "text": format_action_line(state, pid, action, amount),
        },
    )
    _advance_after_action(state, pid)


def _advance_after_action(state: dict[str, Any], last_pid: int) -> None:
    alive = living(state)
    if len(alive) == 1:
        move_bets_to_pot(state)
        _award_fold_win(state, alive[0]["id"])
        return

    nxt = next_from(state, last_pid)
    if nxt is not None:
        state["to_act"] = nxt
        state["status"] = (
            "awaiting_human"
            if state["players"][nxt]["is_human"]
            else "awaiting_bot"
        )
        return

    # street complete
    move_bets_to_pot(state)
    _next_street(state)


def _award_fold_win(state: dict[str, Any], winner: int) -> None:
    w = state["players"][winner]
    won = state["pot"]
    w["stack"] += won
    state["result"] = {
        "type": "fold_win",
        "winners": [winner],
        "amount": won,
        "hands": {},
    }
    state["pot"] = 0
    state["to_act"] = None
    state["street"] = "hand_over"
    state["status"] = "hand_over"
    # 观战结束：亮出仍在池中玩家的手牌（含赢家）
    if state.get("watching"):
        state["show_holes"] = True
    replay_add(
        state,
        {
            "type": "result",
            "text": f"其他人弃牌 → {player_tag(w)} 赢池 {won}",
        },
    )


def _next_street(state: dict[str, Any]) -> None:
    for p in state["players"]:
        p["acted"] = False
    state["last_raise_size"] = state["bb"]

    street = state["street"]
    deck: list[str] = state["deck"]

    if street == "preflop":
        state["board"].extend([deck.pop(), deck.pop(), deck.pop()])
        state["street"] = "flop"
    elif street == "flop":
        state["board"].append(deck.pop())
        state["street"] = "turn"
    elif street == "turn":
        state["board"].append(deck.pop())
        state["street"] = "river"
    elif street == "river":
        _showdown(state)
        return
    else:
        return

    replay_add(
        state,
        {
            "type": "street",
            "street": state["street"],
            "board": list(state["board"]),
            "text": f"── {state['street'].upper()}  {cards_str(state['board'])} ──",
        },
    )
    # if all remaining are all-in or only one can act → run out board
    actors = [p for p in living(state) if can_act(p)]
    if len(actors) <= 1:
        _runout_and_showdown(state)
        return

    nxt = first_to_act_postflop(state)
    # first_to_act_postflop uses seats_to_act which needs acted=False; all false so all can_act
    if nxt is None:
        # everyone matched somehow
        _next_street(state)
        return
    state["to_act"] = nxt
    state["status"] = (
        "awaiting_human" if state["players"][nxt]["is_human"] else "awaiting_bot"
    )


def _runout_and_showdown(state: dict[str, Any]) -> None:
    deck: list[str] = state["deck"]
    while len(state["board"]) < 5:
        state["board"].append(deck.pop())
        if len(state["board"]) == 3:
            state["street"] = "flop"
        elif len(state["board"]) == 4:
            state["street"] = "turn"
        else:
            state["street"] = "river"
        replay_add(
            state,
            {
                "type": "street",
                "street": state["street"],
                "board": list(state["board"]),
                "text": f"── {state['street'].upper()}  {cards_str(state['board'])} ──",
            },
        )
    state["street"] = "river"
    _showdown(state)


def _showdown(state: dict[str, Any]) -> None:
    state["street"] = "showdown"
    # ensure contrib includes everything: pot already has chips; rebuild from contrib
    # If pot holds chips but contrib was updated each street — good.
    # Edge: chips in pot from blinds etc. already in contrib via move_bets.

    # Rebuild pots from contrib; pot field should equal sum of pots
    pots = build_pots(state)
    # If contrib empty bug, fall back to single pot among alive
    if not pots and state["pot"] > 0:
        pots = [Pot(amount=state["pot"], eligible=[p["id"] for p in living(state)])]

    scores = {}
    for p in living(state):
        scores[p["id"]] = best_hand(p["hole"], state["board"])

    awards: dict[int, int] = {p["id"]: 0 for p in state["players"]}
    hand_names = {pid: describe_hand(scores[pid]) for pid in scores}

    remaining_pot_check = 0
    for pot in pots:
        remaining_pot_check += pot.amount
        elig = [pid for pid in pot.eligible if pid in scores]
        if not elig:
            continue
        best = max(scores[pid] for pid in elig)
        winners = [pid for pid in elig if scores[pid] == best]
        share = pot.amount // len(winners)
        extra = pot.amount % len(winners)
        for i, pid in enumerate(winners):
            awards[pid] += share + (1 if i < extra else 0)

    for pid, amt in awards.items():
        if amt:
            state["players"][pid]["stack"] += amt

    state["pot"] = 0
    state["result"] = {
        "type": "showdown",
        "winners": [pid for pid, a in awards.items() if a > 0],
        "awards": {str(k): v for k, v in awards.items() if v > 0},
        "hands": {
            str(pid): {
                "cards": state["players"][pid]["hole"],
                "rank": hand_names[pid],
                "score": list(scores[pid]),
            }
            for pid in scores
        },
    }
    state["to_act"] = None
    state["street"] = "hand_over"
    state["status"] = "hand_over"
    state["show_holes"] = True
    bits = []
    for pid in sorted(scores.keys()):
        p = state["players"][pid]
        amt = awards.get(pid, 0)
        hole = cards_str(p["hole"])
        tag = " ★赢家" if amt > 0 else ""
        won = f" +{amt}" if amt else ""
        bits.append(f"{player_tag(p)} [{hole}] {hand_names[pid]}{won}{tag}")
    replay_add(
        state,
        {
            "type": "result",
            "text": "摊牌 → " + ("；".join(bits) if bits else "无奖池"),
        },
    )


# ── bot styles & policy ─────────────────────────────────────────────────────

# 经典桌型：松紧 × 凶弱 + 弱鱼/疯子等
STYLE_DEFS: dict[str, dict[str, Any]] = {
    "tag": {
        "label": "紧凶",
        "vpip": 0.26,
        "agg": 0.62,
        "call_soft": 0.22,
        "bluff": 0.16,
        "stack_off": 0.55,
        "cbet": 0.72,
    },
    "lag": {
        "label": "松凶",
        "vpip": 0.42,
        "agg": 0.72,
        "call_soft": 0.32,
        "bluff": 0.30,
        "stack_off": 0.50,
        "cbet": 0.78,
    },
    "nit": {
        "label": "超紧",
        "vpip": 0.12,
        "agg": 0.48,
        "call_soft": 0.12,
        "bluff": 0.06,
        "stack_off": 0.70,
        "cbet": 0.40,
    },
    "rock": {
        "label": "紧弱",
        "vpip": 0.18,
        "agg": 0.18,
        "call_soft": 0.35,
        "bluff": 0.05,
        "stack_off": 0.65,
        "cbet": 0.28,
    },
    "station": {
        "label": "跟注站",
        "vpip": 0.48,
        "agg": 0.12,
        "call_soft": 0.88,
        "bluff": 0.04,
        "stack_off": 0.35,
        "cbet": 0.22,
    },
    "maniac": {
        "label": "疯子",
        "vpip": 0.72,
        "agg": 0.88,
        "bluff": 0.52,
        "call_soft": 0.40,
        "stack_off": 0.30,
        "cbet": 0.90,
    },
    "fish": {
        "label": "弱鱼",
        "vpip": 0.55,
        "agg": 0.28,
        "call_soft": 0.78,
        "bluff": 0.14,
        "stack_off": 0.28,
        "cbet": 0.45,
    },
}

# 开桌时加权随机（弱鱼/跟注站略多，桌面更像娱乐局）
STYLE_WEIGHTS: list[tuple[str, float]] = [
    ("tag", 1.2),
    ("lag", 1.0),
    ("nit", 0.7),
    ("rock", 0.8),
    ("station", 1.3),
    ("maniac", 0.6),
    ("fish", 1.4),
]


def pick_style(rng: random.Random) -> str:
    keys = [k for k, _ in STYLE_WEIGHTS]
    weights = [w for _, w in STYLE_WEIGHTS]
    return rng.choices(keys, weights=weights, k=1)[0]


def hole_strength(hole: list[str]) -> float:
    """粗评起手牌 0~1，供松紧门槛使用。"""
    if len(hole) < 2:
        return 0.0
    v1, v2 = RANK_VAL[hole[0][0]], RANK_VAL[hole[1][0]]
    s1, s2 = hole[0][1], hole[1][1]
    hi, lo = max(v1, v2), min(v1, v2)
    suited = s1 == s2
    gap = hi - lo
    if v1 == v2:
        return min(1.0, 0.52 + hi / 30.0)
    score = (hi * 1.15 + lo * 0.55) / 36.0
    if suited:
        score += 0.09
    if gap == 1:
        score += 0.11
    elif gap == 2:
        score += 0.06
    elif gap >= 5 and hi < 14:
        score -= 0.08
    if hi == 14:
        score += 0.10
    if lo >= 11:
        score += 0.07
    return max(0.02, min(0.98, score))


def board_strength(hole: list[str], board: list[str]) -> float:
    """翻后牌力档位，便于驱动下注（不再挤在 0.1~0.2）。"""
    if len(board) < 3:
        return hole_strength(hole)
    cat = best_hand(hole, board)[0]
    # 0高牌 1一对 2两对 3三条 …
    table = {
        0: 0.20,
        1: 0.48,
        2: 0.66,
        3: 0.78,
        4: 0.86,
        5: 0.90,
        6: 0.94,
        7: 0.97,
        8: 0.99,
    }
    base = table.get(cat, 0.2)
    # 有超对/顶对时略抬（用起手牌高点近似）
    hs = hole_strength(hole)
    if cat == 1 and hs >= 0.55:
        base = min(0.62, base + 0.08)
    return base


def _raise_target(state: dict[str, Any], p: dict[str, Any], mult: float = 2.5) -> int:
    mb = max_bet(state)
    pot = state["pot"] + sum(x["bet"] for x in state["players"])
    mrt = min_raise_to(state)
    # 常见池赔注：约 1/2~2/3 pot
    add = max(state["bb"], int(pot * 0.55))
    want = max(mrt, mb + add)
    if mult >= 3.0:
        want = max(want, mb + int(pot * 0.85))
    return min(p["bet"] + p["stack"], want)


def bot_decide(state: dict[str, Any], pid: int) -> tuple[str, Optional[int]]:
    p = state["players"][pid]
    style_id = p.get("style") or "fish"
    prof = STYLE_DEFS.get(style_id, STYLE_DEFS["fish"])
    mb = max_bet(state)
    to_call = mb - p["bet"]
    pot = state["pot"] + sum(x["bet"] for x in state["players"])
    rng = random.SystemRandom()
    street = state["street"]
    n_alive = len(living(state))

    strength = board_strength(p.get("hole") or [], state.get("board") or [])
    continue_bar = max(0.08, min(0.70, 0.78 - prof["vpip"]))
    strong_bar = continue_bar + 0.16
    can_raise = p["stack"] > max(0, to_call)

    # ── 无人下注：过牌或主动进攻 ──
    if to_call <= 0:
        if not can_raise:
            return "check", None

        if street == "preflop":
            # 起手：够强则加注，否则按松紧偶尔偷盲
            if strength >= strong_bar and rng.random() < 0.55 + prof["agg"] * 0.4:
                return "raise", _raise_target(state, p, 2.6)
            if strength >= continue_bar and rng.random() < prof["agg"] * 0.5:
                return "raise", _raise_target(state, p, 2.2)
            if rng.random() < prof["bluff"] * 0.7:
                return "raise", _raise_target(state, p, 2.0)
            return "check", None

        # 翻后：价值下注
        if strength >= 0.72 and rng.random() < 0.75 + prof["agg"] * 0.2:
            return "raise", _raise_target(state, p, 3.0)
        if strength >= 0.48 and rng.random() < 0.45 + prof["agg"] * 0.45:
            return "raise", _raise_target(state, p, 2.6)

        # 持续下注 / 半诈唬：不能全员 check 过街
        cbet = float(prof.get("cbet", 0.4))
        if n_alive <= 2:
            cbet = min(0.95, cbet + 0.18)
        elif n_alive >= 4:
            cbet *= 0.75
        if street == "flop":
            street_mod = 1.0
        elif street == "turn":
            street_mod = 0.72
        else:
            street_mod = 0.55
        # 有一点牌力时更爱 stab
        if strength >= 0.35:
            cbet = min(0.95, cbet + 0.12)
        fire = cbet * street_mod
        if rng.random() < fire:
            return "raise", _raise_target(state, p, 2.3)
        if rng.random() < prof["bluff"] * street_mod:
            return "raise", _raise_target(state, p, 2.0)
        return "check", None

    # ── 面对下注 ──
    call_cost_ratio = to_call / max(1, p["stack"])
    pot_odds = to_call / max(1, pot + to_call)

    if call_cost_ratio > 0.45 and strength < strong_bar + 0.05:
        if rng.random() > prof["call_soft"] * 0.55:
            if strength < continue_bar or rng.random() > prof["stack_off"]:
                return "fold", None

    if strength >= 0.72 and can_raise and rng.random() < 0.55 + prof["agg"] * 0.35:
        return "raise", _raise_target(state, p, 3.0)

    if (
        can_raise
        and strength < 0.40
        and rng.random() < prof["bluff"] * prof["agg"] * 0.85
        and to_call <= max(state["bb"] * 4, int(pot * 0.4))
    ):
        return "raise", _raise_target(state, p, 2.5)

    call_chance = prof["call_soft"]
    if strength >= 0.66:
        call_chance = max(call_chance, 0.93)
    elif strength >= 0.48:
        call_chance = max(call_chance, 0.62 + prof["agg"] * 0.2)
    elif strength >= 0.35:
        call_chance = max(call_chance * 0.7, 0.35)
    else:
        call_chance *= 0.4
        call_chance += (1.0 - pot_odds) * 0.12

    if to_call >= p["stack"]:
        if strength >= 0.45 or rng.random() < call_chance * 0.75:
            return "call", None
        return "fold", None

    if rng.random() < call_chance:
        return "call", None
    return "fold", None


def run_bots_until_human_or_end(state: dict[str, Any], max_steps: int = 200) -> None:
    steps = 0
    while state["status"] == "awaiting_bot" and steps < max_steps:
        pid = state["to_act"]
        if pid is None:
            break
        action, amount = bot_decide(state, pid)
        try:
            apply_action(state, pid, action, amount)
        except ActionError:
            mb = max_bet(state)
            p = state["players"][pid]
            if p["bet"] < mb:
                apply_action(state, pid, "call" if p["stack"] > 0 else "fold", None)
            else:
                apply_action(state, pid, "check", None)
        steps += 1


# ── init / next hand ────────────────────────────────────────────────────────


def parse_human_ids(raw: Any, n: int) -> set[int]:
    human_ids: set[int] = set()
    if raw is not None:
        for part in str(raw).split(","):
            part = part.strip()
            if part == "":
                continue
            hid = int(part)
            if hid < 0 or hid >= n:
                die(f"human 座位越界: {hid}")
            human_ids.add(hid)
    if not human_ids:
        human_ids.add(0)
    return human_ids


def next_live_after(players: list[dict[str, Any]], start: int) -> Optional[int]:
    n = len(players)
    for k in range(1, n + 1):
        i = (start + k) % n
        if players[i]["stack"] > 0:
            return i
    return None


def advance_button(prev_button: int, stacks: list[int]) -> int:
    n = len(stacks)
    for k in range(1, n + 1):
        i = (prev_button + k) % n
        if stacks[i] > 0:
            return i
    die("没有仍持有筹码的玩家")
    return 0


def start_new_hand(
    *,
    n: int,
    stacks: list[int],
    human_ids: set[int],
    sb: int,
    bb: int,
    button: int,
    hand_id: int,
    seed: Optional[int],
    names: Optional[list[str]] = None,
    styles: Optional[list[Optional[str]]] = None,
) -> dict[str, Any]:
    if n < 2 or n > 9:
        die("人数须在 2–9")
    if len(stacks) != n:
        die("stacks 长度与人数不符")

    style_rng = make_rng(None if seed is None else seed + 17)
    players = []
    for i in range(n):
        is_human = i in human_ids
        name = (
            names[i]
            if names and i < len(names)
            else default_name(i, human_ids)
        )
        if is_human:
            style_id: Optional[str] = None
            style_label = "Hero"
        else:
            if styles and i < len(styles) and styles[i]:
                style_id = styles[i]
            else:
                style_id = pick_style(style_rng)
            if style_id not in STYLE_DEFS:
                style_id = "fish"
            style_label = STYLE_DEFS[style_id]["label"]
        players.append(
            {
                "id": i,
                "name": name,
                "stack": stacks[i],
                "bet": 0,
                "contrib": 0,
                "hole": [],
                "folded": stacks[i] <= 0,
                "all_in": False,
                "acted": False,
                "is_human": is_human,
                "style": style_id,
                "style_label": style_label,
            }
        )

    alive = [p for p in players if p["stack"] > 0]
    if len(alive) < 2:
        die("有效筹码人数不足 2：本桌结束。可用 /NLHE init --start --fresh 重开")

    if players[button]["stack"] <= 0:
        button = advance_button(button, stacks)

    rng = make_rng(seed)
    deck = new_deck(rng)
    state: dict[str, Any] = {
        "hand_id": hand_id,
        "street": "preflop",
        "pot": 0,
        "board": [],
        "button": button,
        "sb": sb,
        "bb": bb,
        "deck": deck,
        "players": players,
        "to_act": None,
        "status": "idle",
        "last_raise_size": bb,
        "history": [],
        "replay": [],
        "coach_log": [],
        "watching": False,
        "result": None,
        "show_holes": False,
        "seed_used": seed,
        "session": {
            "players": n,
            "sb": sb,
            "bb": bb,
            "human": ",".join(str(i) for i in sorted(human_ids)),
        },
    }

    alive_ids = [p["id"] for p in alive]
    if len(alive_ids) == 2:
        # 有效两人：按钮位打 SB，另一人 BB
        sb_i = button if button in alive_ids else alive_ids[0]
        if button not in alive_ids:
            state["button"] = sb_i
            button = sb_i
        bb_i = alive_ids[0] if alive_ids[1] == sb_i else alive_ids[1]
    else:
        sb_i = next_live_after(players, button)
        assert sb_i is not None
        bb_i = next_live_after(players, sb_i)
        assert bb_i is not None

    def post(i: int, amt: int) -> None:
        p = state["players"][i]
        pay = min(amt, p["stack"])
        p["stack"] -= pay
        p["bet"] += pay
        if p["stack"] == 0:
            p["all_in"] = True

    post(sb_i, sb)
    post(bb_i, bb)
    state["last_raise_size"] = bb

    for _ in range(2):
        for p in state["players"]:
            if not p["folded"] and (p["stack"] > 0 or p["bet"] > 0):
                p["hole"].append(state["deck"].pop())

    replay_add(
        state,
        {
            "type": "street",
            "street": "preflop",
            "board": [],
            "text": "── PREFLOP ──",
        },
    )

    for p in state["players"]:
        p["acted"] = False

    if len(alive_ids) == 2:
        state["to_act"] = (
            button if can_act(state["players"][button]) else next_from(state, button)
        )
    else:
        state["to_act"] = next_from(state, bb_i)

    ta = state["to_act"]
    if ta is not None and can_act(state["players"][ta]):
        state["status"] = (
            "awaiting_human"
            if state["players"][ta]["is_human"]
            else "awaiting_bot"
        )
    else:
        move_bets_to_pot(state)
        _runout_and_showdown(state)

    run_bots_until_human_or_end(state)
    return state


def finish_and_print(state: dict[str, Any]) -> None:
    try:
        import nlhe_coach

        nlhe_coach.sync_coach_log(state, eval_fn=best_hand)
    except Exception:
        pass
    save_state(state)
    print_display(state)


def style_roster_text(state: dict[str, Any]) -> str:
    bits = []
    for p in state["players"]:
        if p.get("is_human"):
            bits.append(f"{p['id']}:Hero")
        else:
            bits.append(f"{p['id']}:{p.get('style_label') or p.get('style') or '?'}")
    return "Styles: " + " | ".join(bits)


def replay_text(state: dict[str, Any]) -> str:
    replay = state.get("replay") or []
    if not replay:
        return ""
    if state.get("status") != "hand_over" and not state.get("watching"):
        return ""
    title = "观战回放" if state.get("watching") else "本手回放"
    lines = [f"── {title} ──"]
    cur_street = None
    for ev in replay:
        typ = ev.get("type")
        if typ == "street":
            lines.append(ev.get("text") or "")
            cur_street = ev.get("street")
        elif typ == "watch":
            lines.append(f"  * {ev.get('msg')}")
        elif typ == "act":
            st = ev.get("street")
            if st and st != cur_street:
                lines.append(f"── {str(st).upper()} ──")
                cur_street = st
            lines.append(f"  · {ev.get('text')}")
        elif typ == "result":
            lines.append(f"  => {ev.get('text')}")
    return "\n".join(lines)


def actions_hint_text(state: dict[str, Any]) -> str:
    if state["status"] == "awaiting_human":
        acts = legal_actions(state)
        return "\n".join(
            [
                "── 轮到你 ──",
                "Actions: " + " | ".join(acts),
                "示例: fold | check | call | raise 30 | allin",
                "或: /NLHE fold 等",
            ]
        )
    if state["status"] == "hand_over":
        return "\n".join(
            [
                "── 本手结束 ──",
                "继续下一手（保留筹码）: /NLHE next",
                "整桌重开: /NLHE init --start --fresh",
            ]
        )
    return ""


def build_display(state: dict[str, Any]) -> str:
    parts = [render(state), style_roster_text(state)]
    replay = replay_text(state)
    if replay:
        parts.append(replay)
    hint = actions_hint_text(state)
    if hint:
        parts.append(hint)
    return "\n".join(parts)


def print_display(state: dict[str, Any]) -> None:
    print(UI_BEGIN)
    print(build_display(state))
    print(UI_END)


def print_style_roster(state: dict[str, Any]) -> None:
    print(style_roster_text(state))


def print_replay(state: dict[str, Any]) -> None:
    text = replay_text(state)
    if text:
        print(text)


def print_actions_hint(state: dict[str, Any]) -> None:
    text = actions_hint_text(state)
    if text:
        print(text)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def read_skills_lock_entry() -> Optional[dict[str, Any]]:
    """Return nlhe entry from ~/.agents/.skill-lock.json if installed via skills CLI."""
    if not SKILLS_LOCK_PATH.is_file():
        return None
    try:
        lock = json.loads(SKILLS_LOCK_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    entry = (lock.get("skills") or {}).get(SKILL_NAME)
    return entry if isinstance(entry, dict) else None


def render_skills_pkg_static_hint() -> list[str]:
    """Fast hint for init config (no network)."""
    skill_v = read_skill_version() or "?"
    entry = read_skills_lock_entry()
    lines = ["", "【Skill 包更新】（skills.sh / npx skills）"]
    if entry:
        src = entry.get("source") or "?"
        updated = (entry.get("updatedAt") or "")[:10] or "?"
        lines.extend(
            [
                f"  已安装: {SKILL_NAME} ← {src} · 本地 VERSION {skill_v} · 上次同步 {updated}",
                "  检查更新: npx skills check nlhe -g",
                "  安装更新: npx skills update nlhe -g -y && python .nlhe/nlhe_engine.py upgrade",
            ]
        )
    else:
        lines.extend(
            [
                f"  本地 VERSION {skill_v}（未在 skills lock 中，可能为手动 cp 安装）",
                "  若通过 skills.sh 安装: npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y",
                "  检查更新: npx skills check nlhe -g",
            ]
        )
    return lines


def run_skills_check(timeout: int = 45) -> dict[str, Any]:
    """Run `npx skills check nlhe -g` and parse stdout for update status."""
    entry = read_skills_lock_entry()
    try:
        proc = subprocess.run(
            ["npx", "skills", "check", SKILL_NAME, "-g"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        raw = (proc.stdout or "") + (proc.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return {
            "ok": False,
            "status": "error",
            "message": str(e),
            "source": (entry or {}).get("source"),
        }

    plain = _strip_ansi(raw).lower()
    if "no installed skills found matching" in plain:
        return {
            "ok": True,
            "status": "not_tracked",
            "raw": raw,
            "source": None,
        }
    if "update(s) available" in plain or f"↑ {SKILL_NAME}" in _strip_ansi(raw):
        return {
            "ok": True,
            "status": "update_available",
            "raw": raw,
            "source": (entry or {}).get("source"),
        }
    if "found" in plain and "update" in plain and "up to date" not in plain:
        # e.g. "Found 1 global update(s)"
        if SKILL_NAME in plain or f"updating {SKILL_NAME}" in plain:
            return {
                "ok": True,
                "status": "update_available",
                "raw": raw,
                "source": (entry or {}).get("source"),
            }
    if "up to date" in plain:
        return {
            "ok": True,
            "status": "up_to_date",
            "raw": raw,
            "source": (entry or {}).get("source"),
        }
    return {
        "ok": True,
        "status": "unknown",
        "raw": raw,
        "source": (entry or {}).get("source"),
    }


def render_skills_check_report(result: dict[str, Any]) -> str:
    skill_v = read_skill_version() or "?"
    lines = ["── Skill 包更新检查 ──", f"skill:        {SKILL_NAME} v{skill_v}"]
    src = result.get("source")
    if src:
        lines.append(f"source:       {src}")
    status = result.get("status")
    if status == "not_tracked":
        lines.extend(
            [
                "status:       NOT_TRACKED（未通过 npx skills -g 安装）",
                "action:       npx skills add zp342519261/agent-games -g -a cursor -s nlhe -y",
            ]
        )
    elif status == "update_available":
        lines.extend(
            [
                "status:       UPDATE_AVAILABLE",
                "action:       npx skills update nlhe -g -y",
                "then:         python .nlhe/nlhe_engine.py upgrade",
                "",
                "（Agent：向用户说明有新版本，征得同意后再执行上述命令）",
            ]
        )
    elif status == "up_to_date":
        lines.append("status:       UP_TO_DATE")
    elif status == "error":
        lines.append(f"status:       ERROR ({result.get('message')})")
        lines.append("action:       稍后重试 npx skills check nlhe -g")
    else:
        lines.append("status:       UNKNOWN（见下方 CLI 原始输出）")
    raw = result.get("raw")
    if raw and status in ("unknown", "update_available"):
        lines.extend(["", "── skills CLI ──", _strip_ansi(raw).strip()])
    return "\n".join(lines)


def cmd_skills_check(_: argparse.Namespace) -> None:
    result = run_skills_check()
    print(render_skills_check_report(result))
    if result.get("status") == "update_available":
        raise SystemExit(2)


def _load_existing_state_summary() -> Optional[dict[str, Any]]:
    if not STATE_PATH.is_file():
        return None
    try:
        old = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"broken": True}
    players = old.get("players") or []
    sess = old.get("session") or {}
    return {
        "hand_id": old.get("hand_id"),
        "status": old.get("status"),
        "n_players": len(players),
        "stacks": [p.get("stack") for p in players],
        "human_ids": [p["id"] for p in players if p.get("is_human")],
        "sb": sess.get("sb", old.get("sb")),
        "bb": sess.get("bb", old.get("bb")),
        "street": old.get("street"),
    }


def render_init_config(args: argparse.Namespace) -> str:
    """Show table setup suggestions; does not deal cards."""
    n = args.players
    stack = args.stack
    sb, bb = args.sb, args.bb
    eff_bb = stack // bb if bb else 0
    human_raw = args.human
    lines = [
        "── 开桌配置 ──",
        "",
        "【GTO 教学推荐】（与 preflop-6max-100bb 谱包匹配）",
        "  人数 6 · 筹码 1000 · 盲注 5/10 · 有效深度 100bb",
        "  Hero 座位 0（按钮会轮转）",
        "",
        "【当前 CLI 参数】",
        f"  --players {n}  --stack {stack}  --sb {sb}  --bb {bb}  --human {human_raw}",
        f"  有效深度 ≈ {eff_bb}bb",
    ]
    if args.fresh:
        lines.append("  --fresh         已指定（忽略旧桌）")
    if args.keep_stacks:
        lines.append("  --keep-stacks   已指定（沿用筹码）")
    if args.seed is not None:
        lines.append(f"  --seed {args.seed}")

    existing = _load_existing_state_summary()
    lines.append("")
    if existing is None:
        lines.append("【已有牌局】无 state.json，可直接开新桌。")
    elif existing.get("broken"):
        lines.append("【已有牌局】state.json 损坏，建议 --fresh --start 重开。")
    else:
        lines.extend(
            [
                "【已有牌局】检测到 state.json：",
                f"  手数 #{existing.get('hand_id')} · 状态 {existing.get('status')} · "
                f"街 {existing.get('street')}",
                f"  {existing.get('n_players')} 人 · 盲注 {existing.get('sb')}/{existing.get('bb')} · "
                f"Hero 座位 {existing.get('human_ids')}",
                f"  筹码 {existing.get('stacks')}",
            ]
        )
        if existing.get("status") not in ("hand_over", None) and not args.fresh:
            lines.append("  → 进行中：可用 /NLHE info 查看，或 --fresh --start 整桌重开。")
        elif not args.fresh:
            lines.append("  → 本手已结束：可用 /NLHE next 续桌，或 --fresh --start 整桌重开。")

    lines.extend(
        [
            "",
            "【确认开局】",
            "  满意上述参数后，加上 --start 才会发牌：",
            "",
            "  python .nlhe/nlhe_engine.py init --start --fresh \\",
            f"    --players {n} --stack {stack} --sb {sb} --bb {bb} --human {human_raw}",
            "",
            "  教学预设一键开桌：",
            "  python .nlhe/nlhe_engine.py init --start --fresh \\",
            "    --players 6 --stack 1000 --sb 5 --bb 10 --human 0",
            "",
            "  用户侧: /NLHE init --start --fresh （参数可按需调整）",
        ]
    )
    lines.extend(render_skills_pkg_static_hint())
    return "\n".join(lines)


def cmd_init(args: argparse.Namespace) -> None:
    if not args.start:
        print(render_init_config(args))
        return

    n = args.players
    human_ids = parse_human_ids(args.human, n)
    stack = args.stack
    sb, bb = args.sb, args.bb

    prev_button = -1
    hand_id = 1
    keep = bool(args.keep_stacks) and not args.fresh
    names: Optional[list[str]] = None
    styles: Optional[list[Optional[str]]] = None
    stacks: list[int]

    if STATE_PATH.exists() and not args.fresh:
        try:
            old = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            prev_button = int(old.get("button", -1))
            hand_id = int(old.get("hand_id", 0)) + 1
            if keep and len(old.get("players", [])) == n:
                stacks = [p["stack"] for p in old["players"]]
                names = [p["name"] for p in old["players"]]
                styles = [p.get("style") for p in old["players"]]
                human_ids = {
                    p["id"] for p in old["players"] if p.get("is_human")
                } or human_ids
                sess = old.get("session") or {}
                sb = int(sess.get("sb", old.get("sb", sb)))
                bb = int(sess.get("bb", old.get("bb", bb)))
            else:
                stacks = [stack] * n
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            stacks = [stack] * n
    else:
        stacks = [stack] * n

    button = advance_button(prev_button, stacks) if any(s > 0 for s in stacks) else 0
    state = start_new_hand(
        n=n,
        stacks=stacks,
        human_ids=human_ids,
        sb=sb,
        bb=bb,
        button=button,
        hand_id=hand_id,
        seed=args.seed,
        names=names,
        styles=styles,
    )
    finish_and_print(state)


def cmd_next(args: argparse.Namespace) -> None:
    """保留筹码/人数/盲注/人类座位，按钮前移，开下一手。"""
    old = load_state()
    if old.get("status") != "hand_over":
        die(
            f"当前状态是 {old.get('status')}，未结束不可 next。"
            "请先打完本手，或 /NLHE info 查看"
        )

    players_old = old["players"]
    n = len(players_old)
    stacks = [p["stack"] for p in players_old]
    names = [p["name"] for p in players_old]
    styles = [p.get("style") for p in players_old]
    human_ids = {p["id"] for p in players_old if p.get("is_human")} or {0}
    sess = old.get("session") or {}
    sb = int(sess.get("sb", old.get("sb", 5)))
    bb = int(sess.get("bb", old.get("bb", 10)))
    hand_id = int(old.get("hand_id", 0)) + 1
    button = advance_button(int(old.get("button", -1)), stacks)

    state = start_new_hand(
        n=n,
        stacks=stacks,
        human_ids=human_ids,
        sb=sb,
        bb=bb,
        button=button,
        hand_id=hand_id,
        seed=args.seed,
        names=names,
        styles=styles,
    )
    finish_and_print(state)


# ── render ──────────────────────────────────────────────────────────────────


def legal_actions(state: dict[str, Any]) -> list[str]:
    if state["status"] != "awaiting_human" or state["to_act"] is None:
        return []
    p = state["players"][state["to_act"]]
    mb = max_bet(state)
    acts = ["fold"]
    if p["bet"] == mb:
        acts.append("check")
    else:
        acts.append("call")
    mrt = min_raise_to(state)
    if p["stack"] > mb - p["bet"]:
        acts.append(f"raise <n>≥{mrt}")
    acts.append("allin")
    return acts


def print_actions_hint(state: dict[str, Any]) -> None:
    if state["status"] == "awaiting_human":
        acts = legal_actions(state)
        print("── 轮到你 ──")
        print("Actions:", " | ".join(acts))
        print("示例: fold | check | call | raise 30 | allin")
        print("或: /NLHE fold 等")
    elif state["status"] == "hand_over":
        print("── 本手结束 ──")
        print("继续下一手（保留筹码）: /NLHE next")
        print("整桌重开: /NLHE init --start --fresh")


_TABLE_LAYOUTS: dict[int, list[str]] = {
    2: ["S", "N"],
    3: ["S", "NW", "NE"],
    4: ["S", "W", "N", "E"],
    5: ["S", "SW", "NW", "NE", "SE"],
    6: ["S", "SW", "W", "N", "E", "SE"],
    7: ["S", "SW", "W", "NW", "N", "NE", "SE"],
    8: ["S", "SW", "W", "NW", "N", "NE", "E", "SE"],
    9: ["S", "SW", "W", "NW", "N", "NE", "E", "SE", "C"],
}

# 方案 A：各方位锚点 (row, col)，画布高度约 20
_SLOT_POS: dict[str, tuple[int, int]] = {
    "C": (0, 28),
    "N": (1, 28),
    "NE": (4, 50),
    "E": (8, 52),
    "SE": (12, 50),
    "S": (16, 28),
    "SW": (12, 2),
    "W": (8, 1),
    "NW": (4, 2),
}


def _hero_id(state: dict[str, Any]) -> int:
    for p in state["players"]:
        if p.get("is_human"):
            return p["id"]
    return 0


def _seat_to_slot(state: dict[str, Any]) -> dict[str, int]:
    n = len(state["players"])
    layout = list(_TABLE_LAYOUTS.get(n, _TABLE_LAYOUTS[9][:n]))
    hero = _hero_id(state)
    mapping: dict[str, int] = {}
    for i, slot in enumerate(layout):
        mapping[slot] = (hero + i) % n
    return mapping


def _seat_lines(state: dict[str, Any], pid: int) -> list[str]:
    """方案 A 座位三行：头衔 / 手牌 / 筹码。"""
    p = state["players"][pid]
    show_all = bool(state.get("show_holes") or state["street"] == "hand_over")

    flags = []
    if p["id"] == state["button"]:
        flags.append("D")
    if state.get("to_act") == p["id"]:
        flags.append("<")
    if p["folded"]:
        flags.append("X")
    if p["all_in"]:
        flags.append("AI")
    flag = (" " + " ".join(flags)) if flags else ""

    style = p.get("style_label") or ""
    if p.get("is_human"):
        head = f"{p['id']}* You{flag}"
    else:
        head = f"{p['id']} {style} {p['name']}{flag}".replace("  ", " ").strip()
        if len(head) > 18:
            head = f"{p['id']} {style}{flag}".strip()

    if p.get("is_human") and p.get("hole"):
        holes = cards_str(p["hole"])
    elif show_all and p.get("hole"):
        holes = cards_str(p["hole"])
    elif p["folded"]:
        holes = "-- --"
    elif p.get("hole"):
        holes = "?? ??"
    else:
        holes = "-- --"

    if p["bet"]:
        chips = f"{p['stack']}  bet{p['bet']}"
    else:
        chips = str(p["stack"])

    return [head, holes, chips]


def _group_street_actions(state: dict[str, Any]) -> dict[str, list[str]]:
    """按街道汇总 replay 中的行动文案。"""
    streets = ["preflop", "flop", "turn", "river"]
    grouped: dict[str, list[str]] = {s: [] for s in streets}
    for ev in state.get("replay") or []:
        if ev.get("type") != "act":
            continue
        st = ev.get("street")
        if st in grouped and ev.get("text"):
            grouped[st].append(str(ev["text"]))
    return grouped


def _panel_streets(state: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """返回 (上一轮街道, 这一轮街道)。"""
    order = ["preflop", "flop", "turn", "river"]
    cur = state.get("street", "preflop")
    if cur not in order:
        grouped = _group_street_actions(state)
        for s in reversed(order):
            if grouped[s]:
                cur = s
                break
        else:
            cur = "preflop"
    idx = order.index(cur)
    prev = order[idx - 1] if idx > 0 else None
    return prev, cur


STREET_CN: dict[str, str] = {
    "preflop": "翻前",
    "flop": "翻牌",
    "turn": "转牌",
    "river": "河牌",
}


def _render_action_panel(title: str, street: Optional[str], actions: list[str], width: int) -> list[str]:
    inner_w = width - 4
    if street is None:
        label = f"{title} · —"
        body = ["  （第一手 / 无上一轮）"]
    else:
        cn = STREET_CN.get(street, street)
        label = f"{title} · {cn} {street.upper()}"
        if not actions:
            body = ["  （暂无行动）"]
        else:
            body = [f"  · {a}" for a in actions]
    lines = [f"┌─ {label}" + "─" * max(0, inner_w - len(label) - 1) + "┐"]
    for row in body:
        if len(row) > inner_w:
            row = row[: inner_w - 1] + "…"
        lines.append("│" + row.ljust(inner_w) + "│")
    lines.append("└" + "─" * inner_w + "┘")
    return lines


def _pad_panel_lines(lines: list[str], target: int, width: int) -> list[str]:
    if len(lines) >= target:
        return lines
    if not lines:
        return lines
    inner = width - 2
    top, bottom = lines[0], lines[-1]
    body = lines[1:-1]
    blank = "│" + " " * inner + "│"
    while len(body) + 2 < target:
        body.append(blank)
    return [top, *body, bottom]


def render_action_panels(state: dict[str, Any], width: int = 72) -> list[str]:
    """双栏：上一轮 / 这一轮 操作面板。"""
    grouped = _group_street_actions(state)
    prev_st, cur_st = _panel_streets(state)
    half = (width - 3) // 2
    left = _render_action_panel("上一轮", prev_st, grouped.get(prev_st or "", []), half)
    right = _render_action_panel("这一轮", cur_st, grouped.get(cur_st or "", []), half)
    rows = max(len(left), len(right))
    left = _pad_panel_lines(left, rows, half)
    right = _pad_panel_lines(right, rows, half)
    merged: list[str] = []
    for i in range(rows):
        merged.append(left[i] + "   " + right[i])
    return merged


def _paste(canvas: list[list[str]], row: int, col: int, text: str) -> None:
    h = len(canvas)
    w = len(canvas[0]) if h else 0
    for i, ch in enumerate(text):
        r, c = row, col + i
        if 0 <= r < h and 0 <= c < w:
            canvas[r][c] = ch


def hand_preview_text(state: dict[str, Any]) -> str:
    """牌型预览：进行中显示 Hero；摊牌/亮牌显示所有未弃牌者最高牌型。"""
    board = state.get("board") or []
    show_all = bool(state.get("show_holes") or state.get("street") == "hand_over")
    street = state.get("street", "preflop")
    lines: list[str] = []

    # 摊牌 / 观战结束：全员牌型
    if show_all and state.get("status") == "hand_over":
        lines.append("── 摊牌牌型 ──")
        winners = set()
        result = state.get("result") or {}
        if result.get("type") == "showdown":
            winners = set(result.get("winners") or [])
        elif result.get("type") == "fold_win":
            winners = set(result.get("winners") or [])

        shown = False
        for p in state["players"]:
            if p.get("folded") and not (show_all and p.get("hole") and p.get("is_human")):
                # 弃牌者：仅 Hero 可选显示；他人跳过
                if not p.get("is_human"):
                    continue
            if not p.get("hole"):
                continue
            if p.get("folded") and not p.get("is_human"):
                continue
            if p.get("folded") and p.get("is_human"):
                score = best_hand(p["hole"], board) if len(board) >= 3 else best_hand(p["hole"], [])
                lines.append(
                    f"  {p['id']}* You  [{cards_str(p['hole'])}]  "
                    f"{describe_hand(score)}  (已弃)"
                )
                shown = True
                continue
            score = best_hand(p["hole"], board)
            star = " ★赢家" if p["id"] in winners else ""
            who = f"{p['id']}* You" if p.get("is_human") else f"{p['id']} {player_tag(p)}"
            lines.append(
                f"  {who}  [{cards_str(p['hole'])}]  {describe_hand(score)}{star}"
            )
            shown = True
        if not shown:
            lines.append("  （无摊牌手牌）")
        return "\n".join(lines)

    # 进行中：Hero 当前最高牌型预览
    hero = next((p for p in state["players"] if p.get("is_human")), None)
    if not hero or not hero.get("hole"):
        return ""
    score = best_hand(hero["hole"], board)
    label = describe_hand(score)
    if street == "preflop" or len(board) < 3:
        title = "── 牌型预览（起手） ──"
        note = "  ※ 翻牌后按公共牌重算"
    else:
        title = f"── 牌型预览（{STREET_CN.get(street, street)}） ──"
        note = f"  Board: {cards_str(board)}"
    lines = [
        title,
        f"  You  [{cards_str(hero['hole'])}]  →  {label}",
        note,
    ]
    return "\n".join(lines)


def render(state: dict[str, Any]) -> str:
    """方案 A：椭圆毡面牌桌，Hero 在南，中央公共牌。"""
    W, H = 74, 20
    canvas = [[" " for _ in range(W)] for _ in range(H)]

    street_bets = sum(p["bet"] for p in state["players"])
    pot_shown = state["pot"] + street_bets
    board = state["board"]
    if board:
        board_s = " ".join(card_str(c) for c in board)
        if len(board) < 5:
            board_s = board_s + " " + " ".join("·" for _ in range(5 - len(board)))
    else:
        board_s = "· · · · ·"

    watch = ""
    if state.get("watching"):
        watch = "  观战" if state.get("status") != "hand_over" else "  观战结束"

    felt_top = 7
    felt_left = 25
    felt = [
        ".----------------------.",
        f"| {board_s:<20}|",
        f"|     POT {pot_shown:<10}|",
        "'----------------------'",
    ]
    for i, line in enumerate(felt):
        _paste(canvas, felt_top + i, felt_left, line)

    slots = _seat_to_slot(state)
    for slot, pid in slots.items():
        pos = _SLOT_POS.get(slot)
        if not pos:
            continue
        r, c = pos
        seat_lines = _seat_lines(state, pid)
        for i, line in enumerate(seat_lines):
            text = line[:20]
            if slot in ("W", "NW", "SW"):
                _paste(canvas, r + i, c, text)
            elif slot in ("E", "NE", "SE"):
                _paste(canvas, r + i, max(0, min(W - len(text), c + 16 - len(text))), text)
            else:
                _paste(canvas, r + i, max(0, c + 8 - len(text) // 2), text)

    inner = ["".join(row).rstrip() for row in canvas]
    while inner and not inner[-1].strip():
        inner.pop()
    while inner and not inner[0].strip():
        inner.pop(0)

    title = (
        f" NLHE#{state['hand_id']}  {state['street']}  "
        f"pot={pot_shown}  {state['sb']}/{state['bb']}{watch} "
    )
    border_w = max(W, max((len(x) for x in inner), default=W))
    out = ["+" + title.center(border_w, "-") + "+"]
    for row in inner:
        out.append("| " + row.ljust(border_w - 1)[: border_w - 1] + "|")
    out.append("+" + "-" * border_w + "+")

    # 上一轮 / 这一轮 操作面板
    panel_w = max(border_w, 74)
    out.extend(render_action_panels(state, panel_w))

    # 牌型预览 / 摊牌牌型
    preview = hand_preview_text(state)
    if preview:
        out.append(preview)

    try:
        import nlhe_coach

        coach_txt = nlhe_coach.render_coach_block(state, eval_fn=best_hand)
        if coach_txt:
            out.append(coach_txt)
    except Exception:
        out.append("── GTO 教练 ──\n（教练模块未加载）")

    if state.get("result"):
        r = state["result"]
        out.append(
            f"Result: {r.get('type')} winners={r.get('winners')} awards={r.get('awards')}"
        )
        if r.get("hands"):
            for pid, info in r["hands"].items():
                out.append(f"  seat {pid}: {cards_str(info['cards'])}  {info['rank']}")

    return "\n".join(out)



def cmd_info(_: argparse.Namespace) -> None:
    state = load_state()
    try:
        import nlhe_coach

        if nlhe_coach.sync_coach_log(state, eval_fn=best_hand):
            save_state(state)
    except Exception:
        pass
    print_display(state)


def cmd_act(args: argparse.Namespace) -> None:
    state = load_state()
    if state["status"] != "awaiting_human":
        die(f"当前状态不可人工行动: {state['status']}")
    pid = state["to_act"]
    try:
        import nlhe_coach

        nlhe_coach.sync_coach_log(state, eval_fn=best_hand)
    except Exception:
        pass
    try:
        apply_action(state, pid, args.action, args.amount)
    except ActionError as e:
        die(str(e))
    try:
        import nlhe_coach

        nlhe_coach.set_hero_action_on_log(state, pid, args.action)
    except Exception:
        pass
    run_bots_until_human_or_end(state)
    try:
        import nlhe_coach

        nlhe_coach.sync_coach_log(state, eval_fn=best_hand)
    except Exception:
        pass
    save_state(state)
    print_display(state)


def cmd_help(_: argparse.Namespace) -> None:
    text = f"""
NLHE 引擎 v{ENGINE_VERSION}
  init          开桌配置建议（默认不发牌；--start 确认开局）
  skills-check  检查 skills.sh 安装包是否有更新（exit 2 = 有更新）
  next          本手结束后开下一手（保留筹码/人数/盲注/座位）
  info     查看牌桌
  act      行动: fold|check|call|raise|allin
  review   回顾本局 Hero 决策与 GTO 对比（--god 显示底牌）
  charts   列出已安装的 GTO chart pack 与假设
  version  查看本地 / skill 版本与是否需升级
  upgrade  从 skill 模板覆盖同步引擎（保留 state.json）
  help     本帮助

init 参数:
  --start         确认配置并开局（无此参数仅展示配置建议，不发牌）
  --players N     人数 2-9 (默认 6)
  --stack N       起始筹码 (默认 1000)
  --sb N --bb N   盲注 (默认 5/10)
  --human IDS     人类座位，逗号分隔 (默认 0)
  --seed N        可选，复现用
  --fresh         忽略旧桌，全新开局
  --keep-stacks   同人数时沿用上一手筹码（一般用 next 即可）

next 参数:
  --seed N        可选

review 参数:
  --god           额外显示 Hero 底牌

upgrade 参数:
  --force         版本相同也强制覆盖

用户侧 slash:
  /NLHE init | /NLHE init --start | /NLHE skills-check
  /NLHE next | /NLHE info | /NLHE review | /NLHE charts
  /NLHE version | /NLHE upgrade | /NLHE help
  轮到你时: fold | check | call | raise <n> | allin
""".strip()
    print(text)


def cmd_version(_: argparse.Namespace) -> None:
    skill_v = read_skill_version() or "(未找到 skill)"
    marker = read_local_marker_version() or "(无)"
    state_v = None
    if STATE_PATH.is_file():
        try:
            state_v = json.loads(STATE_PATH.read_text(encoding="utf-8")).get(
                "engine_version"
            )
        except (json.JSONDecodeError, OSError):
            state_v = "(state 损坏)"
    outdated, local_v, skill_cmp = needs_upgrade()
    print(f"engine_file:  {ENGINE_PATH}")
    print(f"engine:       {ENGINE_VERSION}")
    print(f"marker:       {marker}")
    print(f"state:        {state_v or '(无 state)'}")
    print(f"skill:        {skill_v}")
    print(f"template:     {SKILL_TEMPLATE}")
    if outdated:
        print(f"status:       OUTDATED  ({local_v} < {skill_cmp})")
        print("action:       运行 /NLHE upgrade 或 python .nlhe/nlhe_engine.py upgrade")
        raise SystemExit(2)
    print("status:       OK")
    entry = read_skills_lock_entry()
    if entry:
        print(f"skills_pkg:   {SKILL_NAME} ← {entry.get('source', '?')} (npx skills)")
        print("skills_check: npx skills check nlhe -g  或  /NLHE skills-check")
    write_local_marker(ENGINE_VERSION)


def sync_charts() -> None:
    src = SKILL_ROOT / "charts"
    dest = STATE_DIR / "charts"
    if not src.is_dir():
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"已同步 charts → {dest}")


def cmd_upgrade(args: argparse.Namespace) -> None:
    if not SKILL_TEMPLATE.is_file():
        die(f"找不到 skill 模板: {SKILL_TEMPLATE}")
    skill_v = read_skill_version() or ENGINE_VERSION
    outdated, local_v, _ = needs_upgrade()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    dest = STATE_DIR / "nlhe_engine.py"
    src = SKILL_TEMPLATE.resolve()
    dest_resolved = dest.resolve()

    if not outdated and not args.force:
        print(f"已是最新: engine={ENGINE_VERSION} skill={skill_v}")
        # 仍刷新 coach + charts（pack 可能独立更新）
        coach_src = SKILL_ROOT / "templates" / "nlhe_coach.py"
        coach_dest = STATE_DIR / "nlhe_coach.py"
        if coach_src.is_file() and coach_src.resolve() != coach_dest.resolve():
            shutil.copy2(coach_src, coach_dest)
            print(f"已同步: {coach_src} -> {coach_dest}")
        sync_charts()
        write_local_marker(ENGINE_VERSION)
        return

    if src == dest_resolved:
        print(f"模板与工作区为同一文件，无需拷贝: {dest}")
    else:
        shutil.copy2(src, dest)
        print(f"已同步: {src} -> {dest}")

    coach_src = SKILL_ROOT / "templates" / "nlhe_coach.py"
    coach_dest = STATE_DIR / "nlhe_coach.py"
    if coach_src.is_file():
        shutil.copy2(coach_src, coach_dest)
        print(f"已同步: {coach_src} -> {coach_dest}")

    sync_charts()

    new_v = skill_v
    for line in dest.read_text(encoding="utf-8").splitlines():
        if line.startswith("ENGINE_VERSION"):
            new_v = line.split("=", 1)[1].strip().strip("\"'")
            break
    write_local_marker(new_v)

    if STATE_PATH.is_file():
        try:
            st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            st["engine_version"] = new_v
            STATE_PATH.write_text(
                json.dumps(st, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"已更新 state.engine_version -> {new_v}（牌局数据未改动）")
        except (json.JSONDecodeError, OSError) as e:
            print(f"警告: 未能写入 state.engine_version: {e}", file=sys.stderr)

    print(f"upgrade OK: {local_v} -> {new_v}")
    print("请使用: python .nlhe/nlhe_engine.py …")


def cmd_review(args: argparse.Namespace) -> None:
    state = load_state()
    try:
        import nlhe_coach

        text = nlhe_coach.render_review(state, god=bool(args.god))
    except Exception as e:
        die(f"review 失败: {e}")
    print(UI_BEGIN)
    print(text)
    print(UI_END)


def cmd_charts(_: argparse.Namespace) -> None:
    try:
        import nlhe_coach

        root = nlhe_coach.charts_root_default()
        text = nlhe_coach.render_charts_list(root)
    except Exception as e:
        die(f"charts 失败: {e}")
    print(UI_BEGIN)
    print(text)
    print(UI_END)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nlhe_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init")
    ini.add_argument("--players", type=int, default=6)
    ini.add_argument("--stack", type=int, default=1000)
    ini.add_argument("--sb", type=int, default=5)
    ini.add_argument("--bb", type=int, default=10)
    ini.add_argument("--human", default="0")
    ini.add_argument("--seed", type=int, default=None)
    ini.add_argument("--fresh", action="store_true")
    ini.add_argument("--keep-stacks", action="store_true")
    ini.add_argument(
        "--start",
        action="store_true",
        help="确认配置并开局（默认 init 仅展示配置建议）",
    )
    ini.set_defaults(func=cmd_init)

    sc = sub.add_parser("skills-check", help="检查 npx skills 安装包更新")
    sc.set_defaults(func=cmd_skills_check)

    nxt = sub.add_parser("next")
    nxt.add_argument("--seed", type=int, default=None)
    nxt.set_defaults(func=cmd_next)

    info = sub.add_parser("info")
    info.set_defaults(func=cmd_info)

    act = sub.add_parser("act")
    act.add_argument("action", choices=["fold", "check", "call", "raise", "allin"])
    act.add_argument("amount", nargs="?", type=int, default=None)
    act.set_defaults(func=cmd_act)

    rev = sub.add_parser("review")
    rev.add_argument("--god", action="store_true", help="额外显示 Hero 底牌")
    rev.set_defaults(func=cmd_review)

    ch = sub.add_parser("charts")
    ch.set_defaults(func=cmd_charts)

    ver = sub.add_parser("version")
    ver.set_defaults(func=cmd_version)

    up = sub.add_parser("upgrade")
    up.add_argument(
        "--force",
        action="store_true",
        help="即使版本相同也强制从模板覆盖",
    )
    up.set_defaults(func=cmd_upgrade)

    hp = sub.add_parser("help")
    hp.set_defaults(func=cmd_help)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

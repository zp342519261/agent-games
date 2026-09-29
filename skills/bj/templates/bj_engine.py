#!/usr/bin/env python3
"""二十一点引擎：洗牌、发牌、点数与胜负。Stdlib only。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== BJ_UI_BEGIN ==="
UI_END = "=== BJ_UI_END ==="

STATE_DIR = Path(".bj")
STATE_PATH = STATE_DIR / "state.json"

RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = ("♠", "♥", "♦", "♣")
BANKROLL_DEFAULT = 1000
BET_MIN = 10


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def emit_ui(body: str) -> None:
    print(UI_BEGIN)
    print(body.rstrip("\n"))
    print(UI_END)


def new_shoe(rng: random.Random, decks: int = 1) -> list[str]:
    cards = [f"{r}{s}" for s in SUITS for r in RANKS] * decks
    rng.shuffle(cards)
    return cards


def card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_total(cards: list[str]) -> tuple[int, bool]:
    """返回 (最佳点数, 是否软牌含按11计的A)。爆牌时返回最小点数。"""
    total = 0
    aces = 0
    for c in cards:
        v = card_value(c)
        total += v
        if c.startswith("A"):
            aces += 1
    soft = False
    while total > 21 and aces:
        total -= 10
        aces -= 1
    if aces and total <= 21:
        soft = True
    return total, soft


def is_blackjack(cards: list[str]) -> bool:
    return len(cards) == 2 and hand_total(cards)[0] == 21


def fmt_cards(cards: list[str], hide_hole: bool = False) -> str:
    if hide_hole and len(cards) >= 2:
        return f"{cards[0]}  ??"
    return "  ".join(cards) if cards else "（空）"


def default_state() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "status": "configuring",
        "bankroll": BANKROLL_DEFAULT,
        "bet_default": 50,
        "decks": 1,
        "seed": None,
        "shoe": [],
        "phase": None,  # betting | player | dealer | settled
        "bet": 0,
        "player": [],
        "dealer": [],
        "doubled": False,
        "outcome": None,
        "payout": 0,
        "message": None,
        "hand_no": 0,
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


def draw(st: dict[str, Any]) -> str:
    if len(st["shoe"]) < 15:
        # 自动重洗
        seed = (st.get("seed") or 0) + st["hand_no"] * 10007 + len(st["shoe"])
        st["shoe"] = new_shoe(random.Random(seed), st["decks"])
    return st["shoe"].pop()


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "二十一点 · 配置",
        "",
        f"筹码：{st['bankroll']}",
        f"默认下注：{st['bet_default']}",
        f"副数：{st['decks']}",
        "",
        "改配置：set --bankroll N --bet N --decks 1|2",
        "确认后 start（可选 --seed）进入下注",
        "规则：Blackjack 3:2；庄家 17 必须停（含软17）；可双倍一次。",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_table(st: dict[str, Any], notice: str = "") -> str:
    phase = st["phase"]
    hide = phase == "player"
    p_total, _ = hand_total(st["player"]) if st["player"] else (0, False)
    if hide:
        d_show = f"{fmt_cards(st['dealer'], hide_hole=True)}"
        d_total_s = "?"
    else:
        d_show = fmt_cards(st["dealer"])
        d_total_s = str(hand_total(st["dealer"])[0]) if st["dealer"] else "-"

    title = {
        "betting": "二十一点 · 下注",
        "player": "二十一点 · 你的回合",
        "dealer": "二十一点 · 庄家回合",
        "settled": "二十一点 · 本手结束",
    }.get(phase or "", "二十一点")

    lines = [
        title,
        "",
        f"筹码：{st['bankroll']}    本手下注：{st['bet'] or '-'}",
        "",
        f"庄家：{d_show}    点数：{d_total_s}",
        f"玩家：{fmt_cards(st['player'])}    点数：{p_total if st['player'] else '-'}",
        "",
    ]
    if phase == "betting":
        lines += [
            f"下注：bet --amount N（默认 {st['bet_default']}，最少 {BET_MIN}）",
            "然后自动发牌。",
        ]
    elif phase == "player":
        lines += [
            "行动：hit 要牌  |  stand 停牌  |  double 双倍（仅两张时）",
        ]
    elif phase == "settled":
        lines += [
            f"结果：{st.get('message') or st.get('outcome')}",
            f"派彩：{st.get('payout', 0):+d}    筹码现为：{st['bankroll']}",
            "",
            "下一手：deal（沿用默认下注）或 bet --amount N",
            "回配置：next",
        ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
    return render_table(st, notice=notice)


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
    die("牌局进行中，要用 next 才会回到配置")


def cmd_set(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置阶段改参数（先 init）")
    if args.bankroll is not None:
        if args.bankroll < BET_MIN:
            die(f"筹码须 ≥ {BET_MIN}")
        st["bankroll"] = args.bankroll
    if args.bet is not None:
        if args.bet < BET_MIN:
            die(f"默认下注须 ≥ {BET_MIN}")
        st["bet_default"] = args.bet
    if args.decks is not None:
        if args.decks not in (1, 2):
            die("副数只能是 1 或 2")
        st["decks"] = args.decks
    if st["bet_default"] > st["bankroll"]:
        die("默认下注不能超过筹码")
    save_state(st)
    emit_ui(render_config(st))


def cmd_start(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置确认后 start")
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    st["seed"] = seed
    st["shoe"] = new_shoe(random.Random(seed), st["decks"])
    st["status"] = "playing"
    st["phase"] = "betting"
    st["bet"] = 0
    st["player"] = []
    st["dealer"] = []
    st["outcome"] = None
    st["payout"] = 0
    st["message"] = None
    st["hand_no"] = 0
    st["doubled"] = False
    save_state(st)
    emit_ui(render(st, notice=f"已洗牌（种子 {seed}）。请下注。"))


def begin_hand(st: dict[str, Any], amount: int) -> str:
    if st["phase"] not in ("betting", "settled"):
        die("现在不能下注")
    if amount < BET_MIN:
        die(f"下注须 ≥ {BET_MIN}")
    if amount > st["bankroll"]:
        die("筹码不足")
    st["bankroll"] -= amount
    st["bet"] = amount
    st["hand_no"] += 1
    st["player"] = [draw(st), draw(st)]
    st["dealer"] = [draw(st), draw(st)]
    st["doubled"] = False
    st["outcome"] = None
    st["payout"] = 0
    st["message"] = None

    # 双方 BJ 检查
    pbj = is_blackjack(st["player"])
    dbj = is_blackjack(st["dealer"])
    if pbj or dbj:
        return settle_blackjack(st, pbj, dbj)

    st["phase"] = "player"
    save_state(st)
    return "发牌完毕，轮到你。"


def settle_blackjack(st: dict[str, Any], pbj: bool, dbj: bool) -> str:
    st["phase"] = "settled"
    bet = st["bet"]
    if pbj and dbj:
        st["outcome"] = "push"
        st["payout"] = bet
        st["bankroll"] += bet
        st["message"] = "双方 Blackjack，推牌。"
    elif pbj:
        win = bet + (bet * 3) // 2
        st["outcome"] = "blackjack"
        st["payout"] = win
        st["bankroll"] += win
        st["message"] = "Blackjack！赔付 3:2。"
    else:
        st["outcome"] = "lose"
        st["payout"] = 0
        st["message"] = "庄家 Blackjack，你输了。"
    save_state(st)
    return st["message"]


def settle(st: dict[str, Any]) -> str:
    """玩家停牌后庄家补牌并结算。"""
    # 庄家补到 >=17
    while True:
        d_total, _ = hand_total(st["dealer"])
        if d_total >= 17:
            break
        st["dealer"].append(draw(st))

    p, _ = hand_total(st["player"])
    d, _ = hand_total(st["dealer"])
    bet = st["bet"]
    st["phase"] = "settled"

    if p > 21:
        st["outcome"] = "bust"
        st["payout"] = 0
        st["message"] = f"你爆牌（{p}）。"
    elif d > 21:
        st["outcome"] = "win"
        st["payout"] = bet * 2
        st["bankroll"] += bet * 2
        st["message"] = f"庄家爆牌（{d}），你赢。"
    elif p > d:
        st["outcome"] = "win"
        st["payout"] = bet * 2
        st["bankroll"] += bet * 2
        st["message"] = f"你 {p} > 庄家 {d}，你赢。"
    elif p < d:
        st["outcome"] = "lose"
        st["payout"] = 0
        st["message"] = f"你 {p} < 庄家 {d}，你输。"
    else:
        st["outcome"] = "push"
        st["payout"] = bet
        st["bankroll"] += bet
        st["message"] = f"同点 {p}，推牌。"
    save_state(st)
    return st["message"]


def cmd_bet(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("请先 start")
    amount = args.amount if args.amount is not None else st["bet_default"]
    notice = begin_hand(st, amount)
    emit_ui(render(st, notice=notice))


def cmd_deal(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("请先 start")
    notice = begin_hand(st, st["bet_default"])
    emit_ui(render(st, notice=notice))


def cmd_hit(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "player":
        die("只能在你的回合要牌")
    st["player"].append(draw(st))
    total, _ = hand_total(st["player"])
    if total > 21:
        notice = settle(st)
    elif total == 21:
        st["phase"] = "dealer"
        notice = settle(st)
    else:
        save_state(st)
        notice = f"要牌 → {total} 点。"
    emit_ui(render(st, notice=notice))


def cmd_stand(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "player":
        die("只能在你的回合停牌")
    st["phase"] = "dealer"
    notice = settle(st)
    emit_ui(render(st, notice=notice))


def cmd_double(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "player":
        die("只能在你的回合双倍")
    if len(st["player"]) != 2 or st["doubled"]:
        die("仅两张起手可双倍一次")
    if st["bankroll"] < st["bet"]:
        die("筹码不足，无法双倍")
    st["bankroll"] -= st["bet"]
    st["bet"] *= 2
    st["doubled"] = True
    st["player"].append(draw(st))
    total, _ = hand_total(st["player"])
    if total > 21:
        notice = settle(st)
    else:
        st["phase"] = "dealer"
        notice = settle(st)
    emit_ui(render(st, notice=notice))


def cmd_info(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    emit_ui(render(st))


def cmd_next(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    keep = {
        "bankroll": st["bankroll"],
        "bet_default": st["bet_default"],
        "decks": st["decks"],
    }
    st = default_state()
    st.update(keep)
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
二十一点引擎 v{ENGINE_VERSION}
  init     进入/重绘配置
  set      --bankroll N --bet N --decks 1|2
  start    [--seed N] 洗牌进入下注
  bet      [--amount N] 下注并发牌
  deal     用默认下注发下一手
  hit / stand / double
  info     当前桌面
  next     回配置（保留筹码）
  help     本帮助

用户侧：
  /二十一点  或  /二十一点 init
  /二十一点 hit  |  stand  |  double  |  next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bj_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (
        ("init", cmd_init),
        ("info", cmd_info),
        ("deal", cmd_deal),
        ("hit", cmd_hit),
        ("stand", cmd_stand),
        ("double", cmd_double),
        ("next", cmd_next),
        ("help", cmd_help),
    ):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    st = sub.add_parser("set")
    st.add_argument("--bankroll", type=int, default=None)
    st.add_argument("--bet", type=int, default=None)
    st.add_argument("--decks", type=int, default=None)
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--seed", type=int, default=None)
    start.set_defaults(func=cmd_start)

    bet = sub.add_parser("bet")
    bet.add_argument("--amount", type=int, default=None)
    bet.set_defaults(func=cmd_bet)

    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

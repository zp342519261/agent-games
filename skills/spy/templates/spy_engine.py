#!/usr/bin/env python3
"""谁是卧底引擎：锁定词对、身份、发言与投票。Stdlib only."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== SPY_UI_BEGIN ==="
UI_END = "=== SPY_UI_END ==="

STATE_DIR = Path(".spy")
STATE_PATH = STATE_DIR / "state.json"

PLAYERS_MIN, PLAYERS_MAX = 3, 8
SPIES_MIN = 1
WORD_MIN, WORD_MAX = 1, 12


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
        "players": 4,
        "spies": 1,
        "user_seat": 1,
        "seed": None,
        "civilian_word": None,
        "spy_word": None,
        "roles": {},  # seat(str) -> "civilian"|"spy"
        "alive": [],
        "round": 0,
        "phase": None,  # describe | vote | ended
        "described": [],
        "descriptions": [],
        "votes": {},  # voter(str) -> target(int)
        "log": [],
        "outcome": None,
        "winner": None,
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


def seat_label(st: dict[str, Any], seat: int) -> str:
    tag = "（你）" if seat == st["user_seat"] else ""
    return f"座位{seat}{tag}"


def alive_seats(st: dict[str, Any]) -> list[int]:
    return list(st["alive"])


def spy_alive(st: dict[str, Any]) -> list[int]:
    return [s for s in st["alive"] if st["roles"][str(s)] == "spy"]


def civilian_alive(st: dict[str, Any]) -> list[int]:
    return [s for s in st["alive"] if st["roles"][str(s)] == "civilian"]


def check_end(st: dict[str, Any]) -> bool:
    spies = spy_alive(st)
    civs = civilian_alive(st)
    if not spies:
        st["status"] = "ended"
        st["phase"] = "ended"
        st["outcome"] = "civilians_win"
        st["winner"] = "平民"
        st["log"].append("全部卧底出局，平民胜利。")
        return True
    if len(spies) >= len(civs):
        st["status"] = "ended"
        st["phase"] = "ended"
        st["outcome"] = "spies_win"
        st["winner"] = "卧底"
        st["log"].append("卧底人数不少于平民，卧底胜利。")
        return True
    return False


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "谁是卧底 · 配置",
        "",
        f"人数：{st['players']}（{PLAYERS_MIN}～{PLAYERS_MAX}）",
        f"卧底数：{st['spies']}",
        f"你的座位：{st['user_seat']}",
        "",
        "改配置：set --players N --spies K --user-seat U",
        "确认后由 Agent 选定词对并 start",
        "词对要相近但不同（如：火车 / 地铁）",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_play(st: dict[str, Any], notice: str = "") -> str:
    phase = st["phase"]
    phase_cn = {"describe": "描述中", "vote": "投票中", "ended": "已结束"}.get(
        phase or "", phase or "?"
    )
    lines = [
        f"谁是卧底 · 第 {st['round']} 轮 · {phase_cn}",
        "",
        f"存活：{', '.join(seat_label(st, s) for s in st['alive'])}",
        f"你的座位：{st['user_seat']}（用 myword 查看自己的词，勿公开角色）",
        "",
    ]
    descs = st.get("descriptions") or []
    round_descs = [d for d in descs if d.get("round") == st["round"]]
    if round_descs:
        lines.append("本轮描述")
        lines.append("------")
        for d in round_descs:
            lines.append(f"{seat_label(st, d['seat'])}：{d['text']}")
        lines.append("")
    if phase == "describe":
        pending = [s for s in st["alive"] if s not in st["described"]]
        lines.append(
            "待描述：" + (", ".join(seat_label(st, s) for s in pending) if pending else "无")
        )
        lines.append("命令：describe --seat N --text …")
        lines.append("全员描述完后自动进入投票。")
    elif phase == "vote":
        voted = sorted(int(k) for k in (st.get("votes") or {}))
        pending = [s for s in st["alive"] if s not in voted]
        lines.append(
            "已投票：" + (", ".join(seat_label(st, s) for s in voted) if voted else "无")
        )
        lines.append(
            "待投票：" + (", ".join(seat_label(st, s) for s in pending) if pending else "无")
        )
        lines.append("命令：vote --voter N --target M")
        lines.append("全员投完后自动计票出局。")
    log = st.get("log") or []
    if log:
        lines += ["", "事件", "------"]
        for item in log[-8:]:
            lines.append(f"· {item}")
    lines += ["", "info 刷新  |  next 新开一局  |  giveup 提前揭晓"]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_ended(st: dict[str, Any], notice: str = "") -> str:
    body = render_play(st).replace(
        f"谁是卧底 · 第 {st['round']} 轮 · 已结束",
        f"谁是卧底 · 结束（{st.get('winner') or '?'}胜）",
        1,
    )
    roles_lines = ["", "身份揭晓", "------"]
    for s in range(1, st["players"] + 1):
        role = st["roles"][str(s)]
        word = st["spy_word"] if role == "spy" else st["civilian_word"]
        mark = "卧底" if role == "spy" else "平民"
        alive = "存活" if s in st["alive"] else "出局"
        roles_lines.append(f"{seat_label(st, s)}：{mark}「{word}」（{alive}）")
    roles_lines += ["", "next 回到配置。"]
    out = body + "\n" + "\n".join(roles_lines)
    if notice:
        out = notice + "\n\n" + out
    return out


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
    if st["status"] == "ended":
        return render_ended(st, notice=notice)
    return render_play(st, notice=notice)


def validate_players_spies(players: int, spies: int) -> None:
    if not (PLAYERS_MIN <= players <= PLAYERS_MAX):
        die(f"人数须为 {PLAYERS_MIN}～{PLAYERS_MAX}")
    if spies < SPIES_MIN or spies >= players:
        die("卧底数须 ≥1 且少于总人数")
    if spies * 2 >= players:
        die("卧底过多（须严格少于半数，保证平民可占优开局）")


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
        die("只能在配置阶段改参数（先 init）")
    players = st["players"] if args.players is None else args.players
    spies = st["spies"] if args.spies is None else args.spies
    user_seat = st["user_seat"] if args.user_seat is None else args.user_seat
    validate_players_spies(players, spies)
    if not (1 <= user_seat <= players):
        die(f"user-seat 须在 1～{players}")
    st["players"] = players
    st["spies"] = spies
    st["user_seat"] = user_seat
    save_state(st)
    emit_ui(render_config(st))


def cmd_start(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置确认后 start")
    civilian = (args.civilian or "").strip()
    spy_w = (args.spy or "").strip()
    if not (WORD_MIN <= len(civilian) <= WORD_MAX):
        die(f"平民词长度须为 {WORD_MIN}～{WORD_MAX}")
    if not (WORD_MIN <= len(spy_w) <= WORD_MAX):
        die(f"卧底词长度须为 {WORD_MIN}～{WORD_MAX}")
    if civilian == spy_w:
        die("平民词与卧底词不能相同")
    validate_players_spies(st["players"], st["spies"])
    if not (1 <= st["user_seat"] <= st["players"]):
        die("user-seat 非法")

    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)
    seats = list(range(1, st["players"] + 1))
    spy_seats = set(rng.sample(seats, st["spies"]))
    roles = {str(s): ("spy" if s in spy_seats else "civilian") for s in seats}

    st["seed"] = seed
    st["civilian_word"] = civilian
    st["spy_word"] = spy_w
    st["roles"] = roles
    st["alive"] = seats[:]
    st["round"] = 1
    st["phase"] = "describe"
    st["described"] = []
    st["descriptions"] = []
    st["votes"] = {}
    st["log"] = [f"开局，种子 {seed}。开始第 1 轮描述。"]
    st["outcome"] = None
    st["winner"] = None
    st["status"] = "playing"
    save_state(st)
    emit_ui(render(st, notice="已发词。玩家用 myword 看自己的词；Agent 用 secret 主持。"))


def cmd_info(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    emit_ui(render(st))


def cmd_secret(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] not in ("playing", "ended"):
        die("只能在开局后读取身份")
    lines = [
        f"平民词：{st['civilian_word']}",
        f"卧底词：{st['spy_word']}",
        f"种子：{st['seed']}",
        "身份：",
    ]
    for s in range(1, st["players"] + 1):
        lines.append(f"  {s}: {st['roles'][str(s)]}")
    print("\n".join(lines))


def cmd_myword(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中查看自己的词")
    seat = st["user_seat"]
    role = st["roles"][str(seat)]
    word = st["spy_word"] if role == "spy" else st["civilian_word"]
    # 只给用户看词，不暴露身份标签
    print(f"你的词：{word}")


def cmd_npcword(args: argparse.Namespace) -> None:
    """仅 Agent：查某座位的词（用于扮演 NPC）。无 UI。"""
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中查询")
    seat = args.seat
    if seat not in st["alive"] and str(seat) not in st["roles"]:
        die("座位不存在")
    if seat == st["user_seat"]:
        die("用户座位请用 myword，不要用 npcword 代替")
    role = st["roles"][str(seat)]
    word = st["spy_word"] if role == "spy" else st["civilian_word"]
    print(f"座位{seat} 角色={role} 词={word}")


def cmd_describe(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "describe":
        die("只能在描述阶段发言")
    seat = args.seat
    text = (args.text or "").strip()
    if seat not in st["alive"]:
        die("该座位已出局或不存在")
    if seat in st["described"]:
        die(f"座位{seat} 本轮已描述过")
    if not text or len(text) > 80:
        die("描述须为 1～80 字")
    st["described"].append(seat)
    st["descriptions"].append({"round": st["round"], "seat": seat, "text": text})
    notice = f"{seat_label(st, seat)} 已描述。"
    if set(st["described"]) >= set(st["alive"]):
        st["phase"] = "vote"
        st["votes"] = {}
        st["log"].append(f"第 {st['round']} 轮描述结束，进入投票。")
        notice = f"第 {st['round']} 轮全员描述完毕，开始投票。"
    save_state(st)
    emit_ui(render(st, notice=notice))


def resolve_votes(st: dict[str, Any]) -> str:
    tallies: dict[int, int] = {}
    for _voter, target in st["votes"].items():
        tallies[target] = tallies.get(target, 0) + 1
    if not tallies:
        return "无人投票。"
    max_v = max(tallies.values())
    top = sorted(s for s, c in tallies.items() if c == max_v)
    detail = "，".join(f"{seat_label(st, s)} {c}票" for s, c in sorted(tallies.items()))
    if len(top) > 1:
        st["log"].append(f"第 {st['round']} 轮平票（{detail}），本轮无人出局。")
        msg = f"平票：{detail}。无人出局。"
    else:
        out = top[0]
        st["alive"] = [s for s in st["alive"] if s != out]
        role = st["roles"][str(out)]
        mark = "卧底" if role == "spy" else "平民"
        st["log"].append(f"第 {st['round']} 轮出局：{seat_label(st, out)}（{mark}）。计票：{detail}")
        msg = f"出局：{seat_label(st, out)}（{mark}）。计票：{detail}"
        if check_end(st):
            return msg + f" 胜负已分：{st['winner']}胜。"
    # 下一轮
    st["round"] += 1
    st["phase"] = "describe"
    st["described"] = []
    st["votes"] = {}
    st["log"].append(f"开始第 {st['round']} 轮描述。")
    return msg + f" 进入第 {st['round']} 轮。"


def cmd_vote(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "vote":
        die("只能在投票阶段投票")
    voter, target = args.voter, args.target
    if voter not in st["alive"]:
        die("投票者不在存活名单")
    if target not in st["alive"]:
        die("投票目标不在存活名单")
    if str(voter) in st["votes"]:
        die(f"座位{voter} 本轮已投过票")
    st["votes"][str(voter)] = target
    notice = f"{seat_label(st, voter)} 已投票。"
    if set(int(k) for k in st["votes"]) >= set(st["alive"]):
        notice = resolve_votes(st)
    save_state(st)
    emit_ui(render(st, notice=notice))


def cmd_giveup(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中提前揭晓")
    st["status"] = "ended"
    st["phase"] = "ended"
    st["outcome"] = "given_up"
    st["winner"] = "无"
    st["log"].append("提前揭晓。")
    save_state(st)
    emit_ui(render(st))


def cmd_next(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    keep = {
        "players": st["players"],
        "spies": st["spies"],
        "user_seat": st["user_seat"],
    }
    st = default_state()
    st.update(keep)
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
谁是卧底引擎 v{ENGINE_VERSION}
  init      进入/重绘配置
  set       --players N --spies K --user-seat U
  start     --civilian 词 --spy 词 [--seed N]
  info      当前 UI
  secret    仅 Agent：词对与全部身份
  myword    打印用户座位的词（不标身份）
  npcword   --seat N  仅 Agent：某座位角色与词
  describe  --seat N --text …
  vote      --voter N --target M
  giveup    提前揭晓
  next      回配置
  help      本帮助

用户侧：
  /卧底  或  /卧底 init
  /卧底 myword  |  /卧底 giveup  |  /卧底 next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="spy_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (
        ("init", cmd_init),
        ("info", cmd_info),
        ("secret", cmd_secret),
        ("myword", cmd_myword),
        ("giveup", cmd_giveup),
        ("next", cmd_next),
        ("help", cmd_help),
    ):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    st = sub.add_parser("set")
    st.add_argument("--players", type=int, default=None)
    st.add_argument("--spies", type=int, default=None)
    st.add_argument("--user-seat", type=int, default=None, dest="user_seat")
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--civilian", required=True)
    start.add_argument("--spy", required=True)
    start.add_argument("--seed", type=int, default=None)
    start.set_defaults(func=cmd_start)

    nw = sub.add_parser("npcword")
    nw.add_argument("--seat", type=int, required=True)
    nw.set_defaults(func=cmd_npcword)

    desc = sub.add_parser("describe")
    desc.add_argument("--seat", type=int, required=True)
    desc.add_argument("--text", required=True)
    desc.set_defaults(func=cmd_describe)

    vt = sub.add_parser("vote")
    vt.add_argument("--voter", type=int, required=True)
    vt.add_argument("--target", type=int, required=True)
    vt.set_defaults(func=cmd_vote)

    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

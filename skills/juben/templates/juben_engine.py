#!/usr/bin/env python3
"""剧本杀引擎：锁定角色本、线索池、阶段与投票真凶。Stdlib only."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== JUBEN_UI_BEGIN ==="
UI_END = "=== JUBEN_UI_END ==="

STATE_DIR = Path(".juben")
STATE_PATH = STATE_DIR / "state.json"

DIFFICULTIES = ("简单", "普通", "困难")
PHASES = ("intro", "search", "discuss", "vote", "ended")
TITLE_MIN, TITLE_MAX = 2, 40
PUBLIC_MIN, PUBLIC_MAX = 20, 400
ROLE_NAME_MIN, ROLE_NAME_MAX = 1, 16
PRIVATE_MIN, PRIVATE_MAX = 20, 800
CLUE_TEXT_MIN, CLUE_TEXT_MAX = 4, 160
MAX_ROLES = 8
MIN_ROLES = 3
MAX_CLUES = 20
MIN_CLUES = 4


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
        "difficulty": "普通",
        "user_role": None,  # role id chosen at config or start
        "seed": None,
        "title": None,
        "public": None,
        "roles": [],  # [{id,name,public,private,is_murderer}]
        "clues": [],  # [{id,text,holder}] holder null=pool, or role id
        "phase": None,
        "round_note": "",
        "drawn": [],  # clue ids revealed publicly
        "votes": {},  # role_id -> target role_id
        "outcome": None,
        "winner_note": None,
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


def parse_json_arg(raw: str, label: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"{label} 不是合法 JSON：{e}")


def validate_script(roles: Any, clues: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(roles, list) or len(roles) < MIN_ROLES:
        die(f"角色至少 {MIN_ROLES} 人")
    if len(roles) > MAX_ROLES:
        die(f"角色不能超过 {MAX_ROLES}")
    cleaned_roles: list[dict[str, Any]] = []
    ids: set[str] = set()
    names: set[str] = set()
    murderers = 0
    for i, r in enumerate(roles):
        if not isinstance(r, dict):
            die(f"角色 {i + 1} 必须是对象")
        rid = (r.get("id") or "").strip()
        name = (r.get("name") or "").strip()
        public = (r.get("public") or "").strip()
        private = (r.get("private") or "").strip()
        is_m = r.get("is_murderer")
        if not rid or rid in ids:
            die("角色 id 必须唯一且非空")
        ids.add(rid)
        nn = len(name)
        if nn < ROLE_NAME_MIN or nn > ROLE_NAME_MAX:
            die(f"角色 {rid} 名称长度非法")
        if name in names:
            die(f"角色名重复：{name}")
        names.add(name)
        pn, privn = len(public), len(private)
        if pn < 4 or pn > 200:
            die(f"角色 {rid} public 长度非法")
        if privn < PRIVATE_MIN or privn > PRIVATE_MAX:
            die(f"角色 {rid} private 长度非法")
        if not isinstance(is_m, bool):
            die(f"角色 {rid} is_murderer 必须是 bool")
        if is_m:
            murderers += 1
        cleaned_roles.append(
            {
                "id": rid,
                "name": name,
                "public": public,
                "private": private,
                "is_murderer": is_m,
            }
        )
    if murderers != 1:
        die("必须恰好 1 名真凶（is_murderer=true）")

    if not isinstance(clues, list) or len(clues) < MIN_CLUES:
        die(f"线索至少 {MIN_CLUES} 条")
    if len(clues) > MAX_CLUES:
        die(f"线索不能超过 {MAX_CLUES}")
    cleaned_clues: list[dict[str, Any]] = []
    cids: set[str] = set()
    for i, c in enumerate(clues):
        if not isinstance(c, dict):
            die(f"线索 {i + 1} 必须是对象")
        cid = (c.get("id") or "").strip()
        text = (c.get("text") or "").strip()
        holder = c.get("holder")
        if not cid or cid in cids:
            die("线索 id 必须唯一且非空")
        cids.add(cid)
        tn = len(text)
        if tn < CLUE_TEXT_MIN or tn > CLUE_TEXT_MAX:
            die(f"线索 {cid} 文本长度非法")
        if holder is not None:
            if not isinstance(holder, str) or holder not in ids:
                die(f"线索 {cid} holder 必须是角色 id 或省略")
        cleaned_clues.append({"id": cid, "text": text, "holder": holder})
    return cleaned_roles, cleaned_clues


def role_by_id(st: dict[str, Any], rid: str) -> dict[str, Any]:
    for r in st["roles"]:
        if r["id"] == rid:
            return r
    die(f"未知角色 id：{rid}")


def role_by_name(st: dict[str, Any], name: str) -> dict[str, Any]:
    for r in st["roles"]:
        if r["name"] == name:
            return r
    die(f"未知角色名：{name}")


def murderer(st: dict[str, Any]) -> dict[str, Any]:
    for r in st["roles"]:
        if r["is_murderer"]:
            return r
    die("内部错误：无真凶")


def phase_cn(phase: Optional[str]) -> str:
    return {
        "intro": "自我介绍",
        "search": "搜证",
        "discuss": "圆桌讨论",
        "vote": "投票",
        "ended": "已结束",
    }.get(phase or "", phase or "?")


def render_config(st: dict[str, Any], notice: str = "") -> str:
    ur = st.get("user_role") or "（开局时指定）"
    lines = [
        "剧本杀 · 配置",
        "",
        f"难度：{st['difficulty']}",
        f"你的角色 id：{ur}",
        "",
        "难度：简单 / 普通 / 困难",
        "可先 set --difficulty D --user-role ROLE_ID",
        "确认后由 Agent 提交剧本 start（含角色本与线索）",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def public_clue_lines(st: dict[str, Any]) -> list[str]:
    drawn = set(st.get("drawn") or [])
    lines = []
    for c in st["clues"]:
        if c["id"] in drawn:
            lines.append(f"· {c['text']}")
    return lines


def render_play(st: dict[str, Any], notice: str = "") -> str:
    user = role_by_id(st, st["user_role"])
    lines = [
        f"剧本杀 · {st['title']} · {phase_cn(st['phase'])}",
        "",
        f"难度：{st['difficulty']}",
        f"你的角色：{user['name']}（用 myrole 看私密剧本，勿公开）",
        "",
        "公开案情",
        "------",
        st["public"] or "",
        "",
        "在场角色",
        "------",
    ]
    for r in st["roles"]:
        tag = "（你）" if r["id"] == st["user_role"] else ""
        lines.append(f"· {r['name']}{tag}：{r['public']}")
    clues = public_clue_lines(st)
    lines += ["", f"已公开线索（{len(clues)}）", "------"]
    if clues:
        lines.extend(clues)
    else:
        lines.append("尚无公开线索。")
    phase = st["phase"]
    lines.append("")
    if phase == "intro":
        lines.append("阶段：各角色按剧本做自我介绍（Agent 扮演 NPC）。")
        lines.append("完成后：phase --to search")
    elif phase == "search":
        pool = [c for c in st["clues"] if c["id"] not in (st.get("drawn") or [])]
        lines.append(f"线索池剩余：{len(pool)}")
        lines.append("draw 抽一张公开；也可 phase --to discuss")
    elif phase == "discuss":
        lines.append("圆桌讨论：玩家发言，Agent 按各角色私密本回应（不剧透真凶）。")
        lines.append("讨论结束：phase --to vote")
    elif phase == "vote":
        voted = sorted(st.get("votes") or {})
        pending = [r["id"] for r in st["roles"] if r["id"] not in voted]
        lines.append("已投票：" + ("、".join(role_by_id(st, i)["name"] for i in voted) if voted else "无"))
        lines.append(
            "待投票："
            + ("、".join(role_by_id(st, i)["name"] for i in pending) if pending else "无")
        )
        lines.append("vote --voter 角色名 --target 角色名")
        lines.append("全员投完后自动开票。")
    lines += ["", "info 刷新  |  myrole 看自己的本  |  giveup 提前揭晓  |  next 新开"]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_ended(st: dict[str, Any], notice: str = "") -> str:
    body = render_play(st).replace(
        f"剧本杀 · {st['title']} · 已结束",
        f"剧本杀 · {st['title']} · 结束",
        1,
    )
    m = murderer(st)
    extra = [
        "",
        "真相揭晓",
        "------",
        st.get("winner_note") or "",
        f"真凶：{m['name']}",
        "",
        "角色私密摘要",
        "------",
    ]
    for r in st["roles"]:
        mark = "【真凶】" if r["is_murderer"] else ""
        extra.append(f"{r['name']}{mark}：{r['private'][:80]}…")
    extra += ["", "next 回到配置。"]
    out = body + "\n" + "\n".join(extra)
    if notice:
        out = notice + "\n\n" + out
    return out


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
    if st["status"] == "ended" or st.get("phase") == "ended":
        return render_ended(st, notice=notice)
    return render_play(st, notice=notice)


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
        die("只能在配置阶段改设置（先 init）")
    if args.difficulty is not None:
        if args.difficulty not in DIFFICULTIES:
            die(f"未知难度：{args.difficulty}")
        st["difficulty"] = args.difficulty
    if args.user_role is not None:
        st["user_role"] = args.user_role.strip() or None
    save_state(st)
    emit_ui(render_config(st))


def cmd_start(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置确认后 start")
    title = (args.title or "").strip()
    public = (args.public or "").strip()
    tn, pn = len(title), len(public)
    if tn < TITLE_MIN or tn > TITLE_MAX:
        die(f"标题须为 {TITLE_MIN}～{TITLE_MAX} 字")
    if pn < PUBLIC_MIN or pn > PUBLIC_MAX:
        die(f"公开案情须为 {PUBLIC_MIN}～{PUBLIC_MAX} 字")
    roles, clues = validate_script(
        parse_json_arg(args.roles_json, "roles-json"),
        parse_json_arg(args.clues_json, "clues-json"),
    )
    user_role = (args.user_role or st.get("user_role") or "").strip()
    if not user_role:
        die("必须指定 --user-role（或配置阶段 set --user-role）")
    if user_role not in {r["id"] for r in roles}:
        die(f"user-role 必须是角色 id 之一：{' / '.join(r['id'] for r in roles)}")
    seed = args.seed
    if seed is not None:
        random.seed(seed)
        # 打乱线索池抽取顺序（仅 holder 为空的进入可抽池顺序）
        pool = [c for c in clues if c["holder"] is None]
        held = [c for c in clues if c["holder"] is not None]
        random.shuffle(pool)
        clues = held + pool

    st["title"] = title
    st["public"] = public
    st["roles"] = roles
    st["clues"] = clues
    st["user_role"] = user_role
    st["seed"] = seed
    st["phase"] = "intro"
    st["drawn"] = []
    # 开局自动公开「持有人为空」以外、标记为开局公开？不——holder 非空的本属私有，drew 时不抽
    # 若线索 holder == 用户，仍不自动公开；玩家用 myclues 看
    st["votes"] = {}
    st["outcome"] = None
    st["winner_note"] = None
    st["status"] = "playing"
    save_state(st)
    emit_ui(render(st))


def cmd_info(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    emit_ui(render(st))


def cmd_myrole(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] == "configuring":
        die("只能在开局后查看自己的剧本")
    user = role_by_id(st, st["user_role"])
    # 无 UI 标记——Agent 可转述给用户本人，但不要贴进公共牌面代码块混用规则：
    # 这里打印纯文本，SKILL 规定可贴给用户（仅自己的本）
    print(f"角色：{user['name']}")
    print("------")
    print(user["private"])
    mine = [c for c in st["clues"] if c.get("holder") == user["id"]]
    if mine:
        print("------")
        print("你的私有线索：")
        for c in mine:
            print(f"· {c['text']}")


def cmd_secret(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] == "configuring":
        die("只能在开局后读取完整剧本")
    payload = {
        "title": st["title"],
        "murderer": murderer(st)["name"],
        "roles": st["roles"],
        "clues": st["clues"],
        "drawn": st["drawn"],
        "phase": st["phase"],
        "votes": st["votes"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_npcrole(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] == "configuring":
        die("只能在开局后读取 NPC 剧本")
    name = (args.name or "").strip()
    r = role_by_name(st, name)
    if r["id"] == st["user_role"]:
        die("这是玩家角色，请用 myrole")
    print(f"角色：{r['name']}")
    print("------")
    print(r["private"])
    mine = [c for c in st["clues"] if c.get("holder") == r["id"]]
    if mine:
        print("------")
        print("私有线索：")
        for c in mine:
            print(f"· {c['text']}")


def cmd_phase(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中切换阶段")
    to = args.to
    cur = st["phase"]
    allowed = {
        "intro": {"search"},
        "search": {"discuss"},
        "discuss": {"vote"},
    }
    if cur not in allowed or to not in allowed[cur]:
        die(f"不能从 {phase_cn(cur)} 切到 {phase_cn(to)}")
    st["phase"] = to
    save_state(st)
    emit_ui(render(st, notice=f"进入「{phase_cn(to)}」阶段。"))


def cmd_draw(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中抽线索")
    if st["phase"] != "search":
        die("只能在搜证阶段 draw")
    drawn = set(st.get("drawn") or [])
    pool = [c for c in st["clues"] if c["holder"] is None and c["id"] not in drawn]
    if not pool:
        emit_ui(render(st, notice="公开线索池已空。可 phase --to discuss"))
        return
    clue = pool[0]
    st["drawn"].append(clue["id"])
    save_state(st)
    emit_ui(render(st, notice=f"公开线索：{clue['text']}"))


def tally_and_end(st: dict[str, Any]) -> None:
    votes = st.get("votes") or {}
    counts: dict[str, int] = {}
    for target in votes.values():
        counts[target] = counts.get(target, 0) + 1
    if not counts:
        die("内部错误：无票")
    max_v = max(counts.values())
    leaders = [rid for rid, n in counts.items() if n == max_v]
    m = murderer(st)
    st["phase"] = "ended"
    st["status"] = "ended"
    if len(leaders) > 1:
        st["outcome"] = "tie_murderer_escape"
        st["winner_note"] = "平票，真凶逃脱。平民失败。"
        return
    accused = leaders[0]
    accused_name = role_by_id(st, accused)["name"]
    if accused == m["id"]:
        st["outcome"] = "civilians_win"
        st["winner_note"] = f"多数票指向 {accused_name}，真凶落网。平民胜利。"
    else:
        st["outcome"] = "murderer_wins"
        st["winner_note"] = f"多数票误指 {accused_name}，真凶逍遥。真凶胜利。"


def cmd_vote(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中投票")
    if st["phase"] != "vote":
        die("只能在投票阶段 vote")
    voter = role_by_name(st, (args.voter or "").strip())
    target = role_by_name(st, (args.target or "").strip())
    if voter["id"] in st["votes"]:
        die(f"{voter['name']} 已经投过票")
    st["votes"][voter["id"]] = target["id"]
    if len(st["votes"]) >= len(st["roles"]):
        tally_and_end(st)
        save_state(st)
        emit_ui(render(st))
        return
    save_state(st)
    emit_ui(render(st, notice=f"{voter['name']} 已投票。"))


def cmd_giveup(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中提前揭晓")
    m = murderer(st)
    st["phase"] = "ended"
    st["status"] = "ended"
    st["outcome"] = "given_up"
    st["winner_note"] = f"主持人提前揭晓。真凶是 {m['name']}。"
    save_state(st)
    emit_ui(render(st))


def cmd_next(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    difficulty = st["difficulty"]
    user_role = st.get("user_role")
    st = default_state()
    st["difficulty"] = difficulty
    # user_role 可能对下一剧本无效，仅保留难度
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
剧本杀引擎 v{ENGINE_VERSION}
  init        进入/重绘配置
  set         --difficulty D [--user-role ROLE_ID]
  start       --title T --public P --roles-json R --clues-json C --user-role ID [--seed N]
  info        查看当前 UI
  myrole      玩家私密剧本（可给用户看，勿混入公共 UI 标记块外规则见 SKILL）
  npcrole     --name 角色名（仅 Agent）
  secret      完整剧本 JSON（不要给用户看）
  phase       --to search|discuss|vote
  draw        搜证阶段抽公开线索
  vote        --voter 名 --target 名
  giveup      提前揭晓
  next        回配置
  help        本帮助

用户侧：
  /剧本杀  或  /剧本杀 init
  /剧本杀 myrole  |  /剧本杀 giveup  |  /剧本杀 next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="juben_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init")
    ini.set_defaults(func=cmd_init)

    st = sub.add_parser("set")
    st.add_argument("--difficulty", default=None)
    st.add_argument("--user-role", default=None, dest="user_role")
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--title", required=True)
    start.add_argument("--public", required=True)
    start.add_argument("--roles-json", required=True, dest="roles_json")
    start.add_argument("--clues-json", required=True, dest="clues_json")
    start.add_argument("--user-role", default=None, dest="user_role")
    start.add_argument("--seed", type=int, default=None)
    start.set_defaults(func=cmd_start)

    info = sub.add_parser("info")
    info.set_defaults(func=cmd_info)

    my = sub.add_parser("myrole")
    my.set_defaults(func=cmd_myrole)

    npc = sub.add_parser("npcrole")
    npc.add_argument("--name", required=True)
    npc.set_defaults(func=cmd_npcrole)

    sec = sub.add_parser("secret")
    sec.set_defaults(func=cmd_secret)

    ph = sub.add_parser("phase")
    ph.add_argument("--to", required=True, choices=["search", "discuss", "vote"])
    ph.set_defaults(func=cmd_phase)

    dr = sub.add_parser("draw")
    dr.set_defaults(func=cmd_draw)

    vt = sub.add_parser("vote")
    vt.add_argument("--voter", required=True)
    vt.add_argument("--target", required=True)
    vt.set_defaults(func=cmd_vote)

    gu = sub.add_parser("giveup")
    gu.set_defaults(func=cmd_giveup)

    nxt = sub.add_parser("next")
    nxt.set_defaults(func=cmd_next)

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

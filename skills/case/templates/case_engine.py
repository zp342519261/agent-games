#!/usr/bin/env python3
"""探案引擎：锁定案情、线索、真凶与搜证进度。Stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== CASE_UI_BEGIN ==="
UI_END = "=== CASE_UI_END ==="

STATE_DIR = Path(".case")
STATE_PATH = STATE_DIR / "state.json"

DIFFICULTIES = ("简单", "普通", "困难")
SURFACE_MIN, SURFACE_MAX = 20, 400
TRUTH_MIN = 30
CULPRIT_MIN, CULPRIT_MAX = 1, 20
MAX_SUSPECTS = 8
MAX_LOCATIONS = 10
MAX_CLUES_PER_LOC = 6
HINT_MIN, HINT_MAX = 4, 120
SECRET_MIN, SECRET_MAX = 4, 200
ASK_ANSWERS = ("是", "不是", "不确定", "拒绝回答")


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
        "surface": None,
        "truth": None,
        "culprit": None,
        "suspects": [],
        "locations": {},  # name -> list[{id,hint,secret}]
        "found": [],  # list of clue ids
        "search_log": [],
        "qa": [],
        "outcome": None,
        "accuse_name": None,
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


def validate_case(
    surface: str,
    truth: str,
    culprit: str,
    suspects: Any,
    locations: Any,
) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    ns, nt, nc = len(surface), len(truth), len(culprit)
    if ns < SURFACE_MIN or ns > SURFACE_MAX:
        die(f"案情简介须为 {SURFACE_MIN}～{SURFACE_MAX} 字（当前 {ns}）")
    if nt < TRUTH_MIN:
        die(f"真相须不少于 {TRUTH_MIN} 字（当前 {nt}）")
    if nc < CULPRIT_MIN or nc > CULPRIT_MAX:
        die(f"真凶名须为 {CULPRIT_MIN}～{CULPRIT_MAX} 字")
    if not isinstance(suspects, list) or len(suspects) < 2:
        die("嫌疑人数至少 2")
    if len(suspects) > MAX_SUSPECTS:
        die(f"嫌疑人数不能超过 {MAX_SUSPECTS}")
    cleaned_suspects: list[str] = []
    for s in suspects:
        if not isinstance(s, str) or not s.strip():
            die("嫌疑人必须是非空字符串")
        name = s.strip()
        if name in cleaned_suspects:
            die(f"重复嫌疑人：{name}")
        cleaned_suspects.append(name)
    if culprit not in cleaned_suspects:
        die("真凶必须在嫌疑人列表中")
    if not isinstance(locations, dict) or not locations:
        die("locations 必须是非空对象")
    if len(locations) > MAX_LOCATIONS:
        die(f"地点数不能超过 {MAX_LOCATIONS}")
    cleaned_locs: dict[str, list[dict[str, str]]] = {}
    seen_ids: set[str] = set()
    total_clues = 0
    for loc, clues in locations.items():
        if not isinstance(loc, str) or not loc.strip():
            die("地点名必须是非空字符串")
        loc_name = loc.strip()
        if not isinstance(clues, list) or not clues:
            die(f"地点「{loc_name}」至少 1 条线索")
        if len(clues) > MAX_CLUES_PER_LOC:
            die(f"地点「{loc_name}」线索不能超过 {MAX_CLUES_PER_LOC}")
        bucket: list[dict[str, str]] = []
        for i, c in enumerate(clues):
            if not isinstance(c, dict):
                die(f"地点「{loc_name}」第 {i + 1} 条线索必须是对象")
            cid = (c.get("id") or "").strip()
            hint = (c.get("hint") or "").strip()
            secret = (c.get("secret") or "").strip()
            if not cid:
                die(f"地点「{loc_name}」线索缺 id")
            if cid in seen_ids:
                die(f"线索 id 重复：{cid}")
            seen_ids.add(cid)
            hn, sn = len(hint), len(secret)
            if hn < HINT_MIN or hn > HINT_MAX:
                die(f"线索 {cid} hint 长度非法")
            if sn < SECRET_MIN or sn > SECRET_MAX:
                die(f"线索 {cid} secret 长度非法")
            bucket.append({"id": cid, "hint": hint, "secret": secret})
            total_clues += 1
        cleaned_locs[loc_name] = bucket
    if total_clues < 3:
        die("全案至少需要 3 条线索")
    return cleaned_suspects, cleaned_locs


def all_clues(st: dict[str, Any]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for loc, clues in st["locations"].items():
        for c in clues:
            out[c["id"]] = {**c, "location": loc}
    return out


def found_hints(st: dict[str, Any]) -> list[str]:
    catalog = all_clues(st)
    lines = []
    for cid in st.get("found") or []:
        c = catalog[cid]
        lines.append(f"[{c['location']}] {c['hint']}")
    return lines


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "探案 · 配置",
        "",
        f"难度：{st['difficulty']}",
        "",
        "难度：简单 / 普通 / 困难",
        "",
        "确认后由 Agent 编好案件再 start。",
        "改配置：set --difficulty D",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_play(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "探案 · 调查中",
        "",
        f"难度：{st['difficulty']}",
        "",
        "案情",
        "------",
        st["surface"] or "",
        "",
        "嫌疑人：" + "、".join(st["suspects"]),
        "地点：" + "、".join(st["locations"].keys()),
        "",
        f"已发现线索：{len(st.get('found') or [])} / {sum(len(v) for v in st['locations'].values())}",
        "",
    ]
    hints = found_hints(st)
    lines.append("笔记本")
    lines.append("------")
    if not hints:
        lines.append("还没有搜到线索。用 search --loc 地点名")
    else:
        for i, h in enumerate(hints, start=1):
            lines.append(f"{i}. {h}")
    qa = st.get("qa") or []
    if qa:
        lines += ["", "询问记录", "------"]
        for i, item in enumerate(qa[-6:], start=1):
            lines.append(f"{i}. 问{item['suspect']}：{item['q']}")
            lines.append(f"   → {item['a']}")
    lines += [
        "",
        "search --loc 地点  |  ask --suspect 名 --q … --a …",
        "accuse --name 真凶名  |  giveup 认输  |  next 新开一局",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_ended(st: dict[str, Any], notice: str = "") -> str:
    outcome = st.get("outcome")
    title = {
        "won": "结案（破案）",
        "wrong": "结案（误判）",
        "given_up": "结案（放弃）",
    }.get(outcome or "", "结案")
    play = render_play(st).replace("探案 · 调查中", f"探案 · {title}", 1)
    extra = [
        "",
        "真相",
        "------",
        st["truth"] or "",
        "",
        f"真凶：{st['culprit']}",
    ]
    if st.get("accuse_name"):
        extra.append(f"你的指控：{st['accuse_name']}")
    extra += ["", "next 回到配置。"]
    out = play + "\n" + "\n".join(extra)
    if notice:
        out = notice + "\n\n" + out
    return out


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
    if st["status"] == "ended":
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
        die("只能在配置阶段改难度（先 init）")
    if args.difficulty is not None:
        if args.difficulty not in DIFFICULTIES:
            die(f"未知难度：{args.difficulty}")
        st["difficulty"] = args.difficulty
    save_state(st)
    emit_ui(render_config(st))


def cmd_start(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置确认后 start")
    surface = (args.surface or "").strip()
    truth = (args.truth or "").strip()
    culprit = (args.culprit or "").strip()
    suspects = parse_json_arg(args.suspects_json, "suspects-json")
    locations = parse_json_arg(args.locations_json, "locations-json")
    cleaned_suspects, cleaned_locs = validate_case(
        surface, truth, culprit, suspects, locations
    )
    st["surface"] = surface
    st["truth"] = truth
    st["culprit"] = culprit
    st["suspects"] = cleaned_suspects
    st["locations"] = cleaned_locs
    st["found"] = []
    st["search_log"] = []
    st["qa"] = []
    st["outcome"] = None
    st["accuse_name"] = None
    st["status"] = "playing"
    save_state(st)
    emit_ui(render(st))


def cmd_info(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    emit_ui(render(st))


def cmd_secret(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] == "configuring":
        die("只能在开局后读取真相")
    payload = {
        "truth": st["truth"],
        "culprit": st["culprit"],
        "locations": st["locations"],
        "found": st["found"],
        "suspects": st["suspects"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在调查中搜证")
    loc = (args.loc or "").strip()
    if loc not in st["locations"]:
        die(f"未知地点：{loc}（可选：{' / '.join(st['locations'])}）")
    found = set(st["found"])
    remaining = [c for c in st["locations"][loc] if c["id"] not in found]
    if not remaining:
        save_state(st)
        emit_ui(render(st, notice=f"「{loc}」已无新线索。"))
        return
    clue = remaining[0]
    st["found"].append(clue["id"])
    st["search_log"].append({"loc": loc, "id": clue["id"]})
    save_state(st)
    emit_ui(render(st, notice=f"在「{loc}」发现：{clue['hint']}"))


def cmd_ask(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在调查中询问")
    suspect = (args.suspect or "").strip()
    if suspect not in st["suspects"]:
        die(f"未知嫌疑人：{suspect}")
    if args.a not in ASK_ANSWERS:
        die(f"回答必须是：{' / '.join(ASK_ANSWERS)}")
    q = (args.q or "").strip()
    if not q:
        die("问题不能为空")
    st["qa"].append({"suspect": suspect, "q": q, "a": args.a})
    save_state(st)
    emit_ui(render(st))


def cmd_accuse(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在调查中指控")
    name = (args.name or "").strip()
    if name not in st["suspects"]:
        die(f"指控对象必须是嫌疑人之一：{' / '.join(st['suspects'])}")
    st["accuse_name"] = name
    st["status"] = "ended"
    if name == st["culprit"]:
        st["outcome"] = "won"
        notice = "指控成立，案件侦破。"
    else:
        st["outcome"] = "wrong"
        notice = "指控错误。"
    save_state(st)
    emit_ui(render(st, notice=notice))


def cmd_giveup(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在调查中认输")
    st["status"] = "ended"
    st["outcome"] = "given_up"
    save_state(st)
    emit_ui(render(st, notice="你放弃了本案。"))


def cmd_next(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    difficulty = st["difficulty"]
    st = default_state()
    st["difficulty"] = difficulty
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
探案引擎 v{ENGINE_VERSION}
  init       进入/重绘配置
  set        --difficulty D
  start      --surface S --truth T --culprit C --suspects-json J --locations-json L
  info       查看当前 UI
  secret     仅 Agent：真相与线索 secret（不要给用户看）
  search     --loc 地点
  ask        --suspect 名 --q 问题 --a 是|不是|不确定|拒绝回答
  accuse     --name 真凶名
  giveup     认输揭底
  next       回配置（保留难度）
  help       本帮助

用户侧：
  /探案  或  /探案 init
  搜证/询问后 accuse；/探案 giveup  |  /探案 next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="case_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init")
    ini.set_defaults(func=cmd_init)

    st = sub.add_parser("set")
    st.add_argument("--difficulty", default=None)
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--surface", required=True)
    start.add_argument("--truth", required=True)
    start.add_argument("--culprit", required=True)
    start.add_argument("--suspects-json", required=True, dest="suspects_json")
    start.add_argument("--locations-json", required=True, dest="locations_json")
    start.set_defaults(func=cmd_start)

    info = sub.add_parser("info")
    info.set_defaults(func=cmd_info)

    sec = sub.add_parser("secret")
    sec.set_defaults(func=cmd_secret)

    search = sub.add_parser("search")
    search.add_argument("--loc", required=True)
    search.set_defaults(func=cmd_search)

    ask = sub.add_parser("ask")
    ask.add_argument("--suspect", required=True)
    ask.add_argument("--q", required=True)
    ask.add_argument("--a", required=True)
    ask.set_defaults(func=cmd_ask)

    accuse = sub.add_parser("accuse")
    accuse.add_argument("--name", required=True)
    accuse.set_defaults(func=cmd_accuse)

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

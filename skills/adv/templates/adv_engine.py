#!/usr/bin/env python3
"""文字冒险引擎：锁定剧情图、道具与结局。Stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== ADV_UI_BEGIN ==="
UI_END = "=== ADV_UI_END ==="

STATE_DIR = Path(".adv")
STATE_PATH = STATE_DIR / "state.json"

GENRES = ("奇幻", "科幻", "悬疑", "日常", "随机")
GENRES_RESOLVED = ("奇幻", "科幻", "悬疑", "日常")
DIFFICULTIES = ("简单", "普通", "困难")
TITLE_MIN, TITLE_MAX = 2, 40
NODE_TEXT_MIN, NODE_TEXT_MAX = 8, 600
CHOICE_LABEL_MIN, CHOICE_LABEL_MAX = 1, 40
MAX_NODES = 40
MAX_CHOICES = 6
OUTCOMES = ("good", "bad", "neutral")


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
        "genre": "随机",
        "difficulty": "普通",
        "genre_resolved": None,
        "title": None,
        "start_node": None,
        "nodes": {},
        "current": None,
        "inventory": [],
        "flags": {},
        "history": [],
        "outcome": None,
        "ending_label": None,
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


def genre_line(st: dict[str, Any]) -> str:
    g = st["genre"]
    r = st.get("genre_resolved")
    if st["status"] != "configuring" and r:
        if g == "随机":
            return f"类型：随机 → {r}"
        return f"类型：{r}"
    return f"类型：{g}"


def parse_json_arg(raw: str, label: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"{label} 不是合法 JSON：{e}")


def validate_scenario(data: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(data, dict):
        die("scenario 必须是对象")
    start = data.get("start")
    nodes = data.get("nodes")
    if not isinstance(start, str) or not start.strip():
        die("scenario.start 必须是非空字符串")
    start = start.strip()
    if not isinstance(nodes, dict) or not nodes:
        die("scenario.nodes 必须是非空对象")
    if len(nodes) > MAX_NODES:
        die(f"节点数不能超过 {MAX_NODES}")
    if start not in nodes:
        die(f"start 节点不存在：{start}")

    normalized: dict[str, Any] = {}
    has_ending = False
    for nid, node in nodes.items():
        if not isinstance(nid, str) or not nid.strip():
            die("节点 id 必须是非空字符串")
        if not isinstance(node, dict):
            die(f"节点 {nid} 必须是对象")
        text = (node.get("text") or "").strip()
        n = len(text)
        if n < NODE_TEXT_MIN or n > NODE_TEXT_MAX:
            die(f"节点 {nid} 正文须为 {NODE_TEXT_MIN}～{NODE_TEXT_MAX} 字（当前 {n}）")
        ending = node.get("ending")
        outcome = node.get("outcome")
        choices_raw = node.get("choices")
        if ending is not None:
            if not isinstance(ending, str) or not ending.strip():
                die(f"节点 {nid} ending 须为非空字符串")
            if outcome not in OUTCOMES:
                die(f"节点 {nid} outcome 须为 {' / '.join(OUTCOMES)}")
            if choices_raw:
                die(f"结局节点 {nid} 不能有 choices")
            has_ending = True
            normalized[nid] = {
                "text": text,
                "ending": ending.strip(),
                "outcome": outcome,
                "choices": [],
            }
            continue
        if not isinstance(choices_raw, list) or not choices_raw:
            die(f"非结局节点 {nid} 至少要有 1 个 choice")
        if len(choices_raw) > MAX_CHOICES:
            die(f"节点 {nid} 选项不能超过 {MAX_CHOICES}")
        choices = []
        for i, ch in enumerate(choices_raw):
            if not isinstance(ch, dict):
                die(f"节点 {nid} 第 {i + 1} 个 choice 必须是对象")
            label = (ch.get("label") or "").strip()
            ln = len(label)
            if ln < CHOICE_LABEL_MIN or ln > CHOICE_LABEL_MAX:
                die(f"节点 {nid} 选项文案长度非法：{label!r}")
            to = ch.get("to")
            if not isinstance(to, str) or to not in nodes:
                die(f"节点 {nid} 选项「{label}」指向不存在的节点：{to}")
            need = ch.get("need") or []
            gain = ch.get("gain") or []
            lose = ch.get("lose") or []
            set_flags = ch.get("set") or {}
            if not isinstance(need, list) or not all(isinstance(x, str) and x.strip() for x in need):
                die(f"节点 {nid} 选项「{label}」need 须为字符串列表")
            if not isinstance(gain, list) or not all(isinstance(x, str) and x.strip() for x in gain):
                die(f"节点 {nid} 选项「{label}」gain 须为字符串列表")
            if not isinstance(lose, list) or not all(isinstance(x, str) and x.strip() for x in lose):
                die(f"节点 {nid} 选项「{label}」lose 须为字符串列表")
            if not isinstance(set_flags, dict) or not all(
                isinstance(k, str) and isinstance(v, bool) for k, v in set_flags.items()
            ):
                die(f"节点 {nid} 选项「{label}」set 须为 bool 字典")
            need_flags = ch.get("need_flags") or {}
            if not isinstance(need_flags, dict) or not all(
                isinstance(k, str) and isinstance(v, bool) for k, v in need_flags.items()
            ):
                die(f"节点 {nid} 选项「{label}」need_flags 须为 bool 字典")
            choices.append(
                {
                    "label": label,
                    "to": to,
                    "need": [x.strip() for x in need],
                    "gain": [x.strip() for x in gain],
                    "lose": [x.strip() for x in lose],
                    "set": dict(set_flags),
                    "need_flags": dict(need_flags),
                }
            )
        normalized[nid] = {"text": text, "ending": None, "outcome": None, "choices": choices}
    if not has_ending:
        die("至少需要一个带 ending/outcome 的结局节点")
    return start, normalized


def visible_choices(st: dict[str, Any], node: dict[str, Any]) -> list[dict[str, Any]]:
    inv = set(st["inventory"])
    flags = st.get("flags") or {}
    out = []
    for ch in node["choices"]:
        if any(item not in inv for item in ch["need"]):
            continue
        ok = True
        for k, v in (ch.get("need_flags") or {}).items():
            if flags.get(k, False) != v:
                ok = False
                break
        if ok:
            out.append(ch)
    return out


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "文字冒险 · 配置",
        "",
        genre_line(st),
        f"难度：{st['difficulty']}",
        "",
        "类型：奇幻 / 科幻 / 悬疑 / 日常 / 随机",
        "难度：简单 / 普通 / 困难",
        "",
        "确认后由 Agent 编好分支剧情再 start。",
        "改配置：set --genre G --difficulty D",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_play(st: dict[str, Any], notice: str = "") -> str:
    node = st["nodes"][st["current"]]
    lines = [
        f"文字冒险 · {st['title']}",
        "",
        f"{genre_line(st)}    难度：{st['difficulty']}",
        "",
        "场景",
        "------",
        node["text"],
        "",
    ]
    inv = st.get("inventory") or []
    lines.append("行囊：" + ("、".join(inv) if inv else "（空）"))
    lines.append("")
    choices = visible_choices(st, node)
    if choices:
        lines.append("选项")
        lines.append("------")
        for i, ch in enumerate(choices, start=1):
            lines.append(f"{i}. {ch['label']}")
        lines.append("")
        lines.append("choose --n N  选择")
    else:
        lines.append("没有可用选项（可能缺道具）。可 giveup 或 next。")
    hist = st.get("history") or []
    if hist:
        lines += ["", "足迹（近 5）", "------"]
        for h in hist[-5:]:
            lines.append(f"· {h}")
    lines += ["", "info 刷新  |  giveup 放弃  |  next 新开一局"]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_ended(st: dict[str, Any], notice: str = "") -> str:
    outcome_cn = {"good": "好结局", "bad": "坏结局", "neutral": "中性结局"}.get(
        st.get("outcome") or "", st.get("outcome") or "?"
    )
    node = st["nodes"][st["current"]]
    lines = [
        f"文字冒险 · 结束（{outcome_cn}）",
        "",
        f"标题：{st['title']}",
        f"{genre_line(st)}    难度：{st['difficulty']}",
        f"结局：{st.get('ending_label') or '?'}",
        "",
        "尾声",
        "------",
        node["text"],
        "",
        "行囊：" + ("、".join(st.get("inventory") or []) or "（空）"),
        "",
        "next 回到配置。",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
    if st["status"] == "ended":
        return render_ended(st, notice=notice)
    return render_play(st, notice=notice)


def apply_arrival(st: dict[str, Any], node_id: str, via: str = "") -> None:
    st["current"] = node_id
    node = st["nodes"][node_id]
    if via:
        st["history"].append(via)
    else:
        st["history"].append(f"抵达「{node_id}」")
    if node.get("ending"):
        st["status"] = "ended"
        st["ending_label"] = node["ending"]
        st["outcome"] = node["outcome"]


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
        die("只能在配置阶段改类型/难度（先 init）")
    if args.genre is not None:
        if args.genre not in GENRES:
            die(f"未知类型：{args.genre}")
        st["genre"] = args.genre
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
    title = (args.title or "").strip()
    tn = len(title)
    if tn < TITLE_MIN or tn > TITLE_MAX:
        die(f"标题须为 {TITLE_MIN}～{TITLE_MAX} 字（当前 {tn}）")
    resolved = args.genre_resolved
    if resolved not in GENRES_RESOLVED:
        die(f"genre-resolved 必须是：{' / '.join(GENRES_RESOLVED)}")
    if st["genre"] != "随机" and resolved != st["genre"]:
        die("genre-resolved 必须与已选类型一致")
    data = parse_json_arg(args.scenario_json, "scenario-json")
    start, nodes = validate_scenario(data)
    st["title"] = title
    st["genre_resolved"] = resolved
    st["start_node"] = start
    st["nodes"] = nodes
    st["inventory"] = []
    st["flags"] = {}
    st["history"] = []
    st["outcome"] = None
    st["ending_label"] = None
    st["status"] = "playing"
    apply_arrival(st, start, via="开局")
    # 若开局即结局（极少见）也允许
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
        die("只能在开局后读取完整剧情图")
    payload = {
        "title": st["title"],
        "start": st["start_node"],
        "current": st["current"],
        "inventory": st["inventory"],
        "flags": st["flags"],
        "nodes": st["nodes"],
        "outcome": st.get("outcome"),
        "ending_label": st.get("ending_label"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_choose(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中选择")
    node = st["nodes"][st["current"]]
    choices = visible_choices(st, node)
    n = args.n
    if n < 1 or n > len(choices):
        die(f"选项须为 1～{len(choices)}（当前可见 {len(choices)}）")
    ch = choices[n - 1]
    inv = list(st["inventory"])
    for item in ch["lose"]:
        if item in inv:
            inv.remove(item)
    for item in ch["gain"]:
        if item not in inv:
            inv.append(item)
    st["inventory"] = inv
    flags = dict(st.get("flags") or {})
    flags.update(ch.get("set") or {})
    st["flags"] = flags
    via = f"选「{ch['label']}」→ {ch['to']}"
    apply_arrival(st, ch["to"], via=via)
    save_state(st)
    emit_ui(render(st))


def cmd_giveup(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中放弃")
    st["status"] = "ended"
    st["outcome"] = "bad"
    st["ending_label"] = "中途放弃"
    st["history"].append("玩家放弃")
    save_state(st)
    emit_ui(render(st, notice="你放弃了这段旅程。"))


def cmd_next(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("还没有配置，请先 init")
    if st["status"] == "configuring":
        emit_ui(render_config(st))
        return
    genre, difficulty = st["genre"], st["difficulty"]
    st = default_state()
    st["genre"] = genre
    st["difficulty"] = difficulty
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
文字冒险引擎 v{ENGINE_VERSION}
  init              进入/重绘配置
  set               --genre G --difficulty D
  start             --title T --scenario-json JSON --genre-resolved R
  info              查看当前 UI
  secret            仅 Agent：完整剧情图 JSON（不要给用户看）
  choose            --n N
  giveup            放弃本局
  next              回配置（保留类型/难度）
  help              本帮助

用户侧：
  /冒险  或  /冒险 init
  确认配置后开始；局中 choose 选分支
  /冒险 giveup  |  /冒险 next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adv_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init")
    ini.set_defaults(func=cmd_init)

    st = sub.add_parser("set")
    st.add_argument("--genre", default=None)
    st.add_argument("--difficulty", default=None)
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--title", required=True)
    start.add_argument("--scenario-json", required=True, dest="scenario_json")
    start.add_argument("--genre-resolved", required=True, dest="genre_resolved")
    start.set_defaults(func=cmd_start)

    info = sub.add_parser("info")
    info.set_defaults(func=cmd_info)

    sec = sub.add_parser("secret")
    sec.set_defaults(func=cmd_secret)

    ch = sub.add_parser("choose")
    ch.add_argument("--n", type=int, required=True)
    ch.set_defaults(func=cmd_choose)

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

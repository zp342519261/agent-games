#!/usr/bin/env python3
"""成语接龙引擎：词库校验、首尾相接、计分。Stdlib only。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Optional

ENGINE_VERSION = "1.0.0"
UI_BEGIN = "=== IDIOM_UI_BEGIN ==="
UI_END = "=== IDIOM_UI_END ==="

STATE_DIR = Path(".idiom")
STATE_PATH = STATE_DIR / "state.json"

# 常用四字成语（可扩展）。引擎只认本表 + 开局后 Agent 经 add 临时加入的词。
IDIOM_BANK: tuple[str, ...] = (
    "一心一意", "一鸣惊人", "一举两得", "一石二鸟", "一帆风顺", "一见钟情",
    "一诺千金", "一窍不通", "一丝不苟", "一马当先", "二话不说", "十全十美",
    "七上八下", "八面玲珑", "九牛一毛", "三人成虎", "三心二意", "三生有幸",
    "大公无私", "大显身手", "大开眼界", "大惊小怪", "口是心非", "才高八斗",
    "千钧一发", "千辛万苦", "万无一失", "万事大吉", "马到成功", "马不停蹄",
    "开门见山", "开天辟地", "天长地久", "天经地义", "天马行空", "无中生有",
    "无忧无虑", "无懈可击", "无与伦比", "不可一世", "不可思议", "不耻下问",
    "不约而同", "不速之客", "日积月累", "日新月异", "中流砥柱", "见义勇为",
    "见多识广", "水到渠成", "水落石出", "水涨船高", "风平浪静", "风驰电掣",
    "风雨同舟", "手到擒来", "手忙脚乱", "手足无措", "心花怒放", "心想事成",
    "心平气和", "心旷神怡", "龙飞凤舞", "画龙点睛", "画蛇添足", "守株待兔",
    "对牛弹琴", "目不转睛", "目瞪口呆", "眉开眼笑", "耳濡目染", "耳目一新",
    "出口成章", "出类拔萃", "出奇制胜", "生龙活虎", "生财有道", "乐在其中",
    "乐极生悲", "四面楚歌", "四通八达", "半途而废", "平易近人", "平步青云",
    "打草惊蛇", "本末倒置", "东山再起", "东张西望", "石破天惊", "左右逢源",
    "司空见惯", "叹为观止", "叶公好龙", "史无前例", "叫苦连天", "另眼相看",
    "功成名就", "功亏一篑", "加油添醋", "包罗万象", "处心积虑", "外强中干",
    "多才多艺", "多此一举", "夜以继日", "夜郎自大", "头头是道", "头破血流",
    "宁死不屈", "安居乐业", "安然无恙", "字字珠玑", "守口如瓶", "兴高采烈",
    "光明正大", "光彩夺目", "先发制人", "全神贯注", "全力以赴", "再接再厉",
    "危机四伏", "危言耸听", "同甘共苦", "同舟共济", "名正言顺", "名列前茅",
    "名副其实", "后发制人", "后顾之忧", "回味无穷", "因材施教", "因地制宜",
    "在所难免", "地大物博", "多多益善", "如火如荼", "如鱼得水", "如雷贯耳",
    "夸夸其谈", "尽善尽美", "尽人皆知", "异想天开", "异口同声", "当机立断",
    "当局者迷", "深思熟虑", "汗马功劳", "江郎才尽", "羊入虎口", "耳熟能详",
    "红光满面", "约法三章", "花好月圆", "花言巧语", "苍翠欲滴", "走马观花",
    "走投无路", "足智多谋", "身临其境", "身不由己", "近水楼台", "近在咫尺",
    "迎刃而解", "返老还童", "冷若冰霜", "言简意赅", "言之有理", "忘恩负义",
    "快马加鞭", "怀才不遇", "忧心忡忡", "闲情逸致", "闷闷不乐", "沧海一粟",
    "沉鱼落雁", "沉默寡言", "完美无缺", "穷途末路", "良药苦口", "花团锦簇",
    "言行一致", "言过其实", "谈笑风生", "纸上谈兵", "纹丝不动", "纷至沓来",
    "纵横驰骋", "脍炙人口", "胆大包天", "胆小如鼠", "背道而驰", "胡思乱想",
    "草木皆兵", "茹毛饮血", "荣华富贵", "南辕北辙", "相得益彰", "相提并论",
    "眉飞色舞", "春风得意", "春暖花开", "柳暗花明", "树大招风", "残羹冷炙",
    "活灵活现", "洗耳恭听", "津津有味", "举一反三", "举足轻重", "举世无双",
    "骄兵必败", "骄奢淫逸", "骇人听闻", "高瞻远瞩", "高枕无忧", "鬼斧神工",
    "鬼鬼祟祟", "凌云壮志", "雪中送炭", "雪上加霜", "捷足先登", "推心置腹",
    "推陈出新", "接二连三", "措手不及", "提纲挈领", "博大精深", "喜出望外",
    "喜气洋洋", "喝西北风", "喋喋不休", "啼笑皆非", "喧宾夺主", "量力而行",
    "量体裁衣", "锐不可当", "锋芒毕露", "错综复杂", "锦上添花", "锦囊妙计",
    "长驱直入", "问心无愧", "阳奉阴违", "阳春白雪", "随机应变", "随遇而安",
    "隐姓埋名", "雄心壮志", "集思广益", "集腋成裘", "明月清风", "朝气蓬勃",
    "朝三暮四", "棋逢对手", "森严壁垒", "温故知新", "溃不成军", "游刃有余",
    "湖光山色", "炉火纯青", "焦头烂额",     "痛心疾首", "痛改前非", "登峰造极",
    "发人深省", "发愤图强", "聪明伶俐", "落井下石", "落花流水", "叶落归根",
    "蛛丝马迹", "跋山涉水", "道貌岸然", "道听途说", "遗臭万年", "销声匿迹",
    "锦绣前程", "锦衣玉食", "错落有致", "长年累月", "长吁短叹", "闻鸡起舞",
    "阳关大道", "阡陌交通", "隔靴搔痒", "雷厉风行", "雷霆万钧", "雾里看花",
    "青出于蓝", "青梅竹马", "非同小可", "面面俱到", "面红耳赤", "鞭长莫及",
    "风和日丽", "飞黄腾达", "飞蛾扑火", "饮水思源", "高谈阔论", "鹤立鸡群",
)


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
        "mode": "solo",  # solo: 用户接龙；duel: 用户与 Agent 轮流
        "target": 10,  # 连续成功目标（solo）或回合上限相关
        "seed": None,
        "extra_words": [],  # Agent 经 add 追加的合法词
        "used": [],
        "current": None,
        "streak": 0,
        "score": 0,
        "turn": "user",  # user | agent
        "phase": None,  # playing | ended
        "outcome": None,
        "message": None,
        "history": [],
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


def all_words(st: dict[str, Any]) -> set[str]:
    return set(IDIOM_BANK) | set(st.get("extra_words") or [])


def is_four_han(word: str) -> bool:
    if len(word) != 4:
        return False
    return all("\u4e00" <= ch <= "\u9fff" for ch in word)


def candidates(st: dict[str, Any], head: str) -> list[str]:
    used = set(st["used"])
    return sorted(w for w in all_words(st) if w[0] == head and w not in used)


def render_config(st: dict[str, Any], notice: str = "") -> str:
    lines = [
        "成语接龙 · 配置",
        "",
        f"模式：{st['mode']}（solo=独自接龙 / duel=与主持轮流）",
        f"目标连击：{st['target']}",
        f"词库：内置 {len(IDIOM_BANK)} + 临时 {len(st.get('extra_words') or [])}",
        "",
        "改配置：set --mode solo|duel --target N",
        "确认后 start（可选 --seed）",
    ]
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render_play(st: dict[str, Any], notice: str = "") -> str:
    phase = st["phase"]
    title = "成语接龙 · 进行中" if phase == "playing" else f"成语接龙 · 结束（{st.get('outcome') or ''}）"
    last = st["current"] or "—"
    need = last[-1] if st["current"] else "?"
    lines = [
        title,
        "",
        f"模式：{st['mode']}    连击：{st['streak']} / 目标 {st['target']}    得分：{st['score']}",
        f"当前成语：{last}",
        f"下一词须以「{need}」开头",
        f"轮到：{'你' if st['turn'] == 'user' else '主持（Agent）'}",
        "",
    ]
    hist = st.get("history") or []
    if hist:
        lines.append("记录")
        lines.append("------")
        for i, h in enumerate(hist[-12:], start=max(1, len(hist) - 11)):
            lines.append(f"{i}. {h['word']}（{h['by']}）")
        lines.append("")
    if phase == "playing":
        if st["turn"] == "user":
            lines.append("你接：play --word 四字成语")
            lines.append("接不上：giveup")
        else:
            lines.append("主持用 agent-play --word …（可先 hint 查看候选）")
        lines.append("提示候选：hint（打印若干可选词，可供参考）")
    else:
        lines.append(st.get("message") or "")
        lines.append("next 回到配置。")
    if notice:
        lines = [notice, ""] + lines
    return "\n".join(lines)


def render(st: dict[str, Any], notice: str = "") -> str:
    if st["status"] == "configuring":
        return render_config(st, notice=notice)
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
        die("只能在配置阶段改参数（先 init）")
    if args.mode is not None:
        if args.mode not in ("solo", "duel"):
            die("mode 须为 solo 或 duel")
        st["mode"] = args.mode
    if args.target is not None:
        if not (3 <= args.target <= 50):
            die("target 须为 3～50")
        st["target"] = args.target
    save_state(st)
    emit_ui(render_config(st))


def cmd_start(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "configuring":
        die("只能在配置确认后 start")
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)
    words = list(all_words(st))
    # 选一个后面还有接龙空间的开局词
    start = None
    for _ in range(40):
        cand = rng.choice(words)
        if candidates({**st, "used": [cand]}, cand[-1]):
            start = cand
            break
    if start is None:
        start = rng.choice(words)
    st["seed"] = seed
    st["used"] = [start]
    st["current"] = start
    st["streak"] = 0
    st["score"] = 0
    st["turn"] = "user"
    st["phase"] = "playing"
    st["status"] = "playing"
    st["outcome"] = None
    st["message"] = None
    st["history"] = [{"word": start, "by": "系统"}]
    save_state(st)
    emit_ui(render(st, notice=f"开局「{start}」（种子 {seed}）。请你接龙。"))


def apply_play(st: dict[str, Any], word: str, by: str) -> str:
    word = word.strip()
    if not is_four_han(word):
        die("须为四个汉字")
    if word not in all_words(st):
        die(f"词库无此词：{word}（可用 add --word 临时收纳后重试）")
    if word in st["used"]:
        die("此词本局已用过")
    need = st["current"][-1]
    if word[0] != need:
        die(f"须以「{need}」开头（你出了「{word[0]}」）")
    st["used"].append(word)
    st["current"] = word
    st["streak"] += 1
    st["score"] += 1
    st["history"].append({"word": word, "by": by})
    notice = f"{by}：{word}（连击 {st['streak']}）"

    if st["mode"] == "solo" and st["streak"] >= st["target"]:
        st["phase"] = "ended"
        st["status"] = "ended"
        st["outcome"] = "通关"
        st["message"] = f"达到目标连击 {st['target']}！"
        return notice + " " + st["message"]

    if st["mode"] == "duel":
        st["turn"] = "agent" if by == "你" else "user"
        # 若下一方无词可接 → 对方胜
        nxt = candidates(st, word[-1])
        if not nxt:
            st["phase"] = "ended"
            st["status"] = "ended"
            if by == "你":
                st["outcome"] = "你胜"
                st["message"] = "主持接不上，你胜。"
            else:
                st["outcome"] = "主持胜"
                st["message"] = "你接不上可选词，主持胜。"
            return notice + " " + st["message"]
    else:
        # solo：检查用户是否还能继续；不能则结束
        nxt = candidates(st, word[-1])
        if not nxt:
            st["phase"] = "ended"
            st["status"] = "ended"
            st["outcome"] = "词穷"
            st["message"] = f"词库已无「{word[-1]}」可接之词。得分 {st['score']}。"
            return notice + " " + st["message"]
        st["turn"] = "user"
    return notice


def cmd_play(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "playing":
        die("只能在进行中出词")
    if st["turn"] != "user":
        die("现在轮到主持，请用 agent-play")
    notice = apply_play(st, args.word, "你")
    save_state(st)
    emit_ui(render(st, notice=notice))


def cmd_agent_play(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing" or st["phase"] != "playing":
        die("只能在进行中出词")
    if st["mode"] != "duel":
        die("仅 duel 模式使用 agent-play")
    if st["turn"] != "agent":
        die("现在轮到用户")
    notice = apply_play(st, args.word, "主持")
    save_state(st)
    emit_ui(render(st, notice=notice))


def cmd_hint(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中提示")
    need = st["current"][-1]
    cands = candidates(st, need)
    # 无 UI：仅 Agent 参考；也可少量展示
    print(f"须接「{need}」· 候选 {len(cands)} 个：")
    print("、".join(cands[:20]) + ("…" if len(cands) > 20 else ""))


def cmd_add(args: argparse.Namespace) -> None:
    st = load_state()
    if st is None:
        die("请先 init")
    word = (args.word or "").strip()
    if not is_four_han(word):
        die("须为四个汉字")
    if word in all_words(st):
        die("词库已有")
    st.setdefault("extra_words", []).append(word)
    save_state(st)
    print(f"已临时收纳：{word}")


def cmd_giveup(_: argparse.Namespace) -> None:
    st = load_state()
    if st is None or st["status"] != "playing":
        die("只能在进行中认输")
    st["phase"] = "ended"
    st["status"] = "ended"
    st["outcome"] = "认输"
    st["message"] = f"认输。连击 {st['streak']}，得分 {st['score']}。"
    save_state(st)
    emit_ui(render(st))


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
        "mode": st["mode"],
        "target": st["target"],
        "extra_words": list(st.get("extra_words") or []),
    }
    st = default_state()
    st.update(keep)
    save_state(st)
    emit_ui(render_config(st))


def cmd_help(_: argparse.Namespace) -> None:
    print(
        f"""
成语接龙引擎 v{ENGINE_VERSION}
  init          配置
  set           --mode solo|duel --target N
  start         [--seed N]
  play          --word 成语
  agent-play    --word 成语（duel）
  hint          打印候选（给 Agent）
  add           --word 成语（临时收纳）
  giveup / info / next / help

用户侧：
  /成语接龙  或  /成语接龙 init
  /成语接龙 play …  |  giveup  |  next
""".strip()
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="idiom_engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (
        ("init", cmd_init),
        ("info", cmd_info),
        ("hint", cmd_hint),
        ("giveup", cmd_giveup),
        ("next", cmd_next),
        ("help", cmd_help),
    ):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    st = sub.add_parser("set")
    st.add_argument("--mode", default=None)
    st.add_argument("--target", type=int, default=None)
    st.set_defaults(func=cmd_set)

    start = sub.add_parser("start")
    start.add_argument("--seed", type=int, default=None)
    start.set_defaults(func=cmd_start)

    pl = sub.add_parser("play")
    pl.add_argument("--word", required=True)
    pl.set_defaults(func=cmd_play)

    ap = sub.add_parser("agent-play")
    ap.add_argument("--word", required=True)
    ap.set_defaults(func=cmd_agent_play)

    ad = sub.add_parser("add")
    ad.add_argument("--word", required=True)
    ad.set_defaults(func=cmd_add)

    return p


def run_cmd(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


def main() -> None:
    run_cmd(sys.argv[1:])


if __name__ == "__main__":
    main()

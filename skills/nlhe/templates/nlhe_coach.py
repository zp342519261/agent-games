from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable, Optional

RANKS = "23456789TJQKA"
SUITS = "cdhs"

RANK_ORDER = "23456789TJQKA"

POS_6MAX = ["BTN", "SB", "BB", "UTG", "HJ", "CO"]
DEPTH_TIERS_P0 = [100]


def normalize_hand(hole: list[str]) -> str:
    if len(hole) != 2:
        raise ValueError("need exactly 2 hole cards")
    r1, s1 = hole[0][0], hole[0][1]
    r2, s2 = hole[1][0], hole[1][1]
    i1, i2 = RANK_ORDER.index(r1), RANK_ORDER.index(r2)
    if i1 < i2:
        r1, r2, s1, s2, i1, i2 = r2, r1, s2, s1, i2, i1
    if r1 == r2:
        return r1 + r2
    return r1 + r2 + ("s" if s1 == s2 else "o")


def pot_odds_needed(pot: int, to_call: int) -> Optional[float]:
    if to_call <= 0:
        return None
    return to_call / (pot + to_call)


def seat_position(button: int, seat: int, n: int) -> str:
    if n != 6:
        return "?"
    return POS_6MAX[(seat - button) % 6]


def build_spot_key(state: dict[str, Any]) -> dict[str, Any]:
    n = len(state["players"])
    key: dict[str, Any] = {
        "game": "NLHE",
        "street": state.get("street"),
        "board_class": None,
    }
    if n != 6:
        key["miss_reason"] = "players_not_6"
        return key
    hero = next(p for p in state["players"] if p.get("is_human"))
    btn = int(state["button"])
    bb = max(1, int(state["bb"]))
    key["hero_pos"] = seat_position(btn, hero["id"], n)
    key["hero_hand"] = normalize_hand(hero["hole"]) if len(hero.get("hole") or []) == 2 else None
    lives = [p for p in state["players"] if not p.get("folded")]
    eff = min(p["stack"] + p["bet"] for p in lives) // bb
    tier = min(DEPTH_TIERS_P0, key=lambda t: abs(t - eff))
    if abs(tier - eff) > 15:
        key["miss_reason"] = "depth_not_in_tier"
        return key
    key["eff_bb"] = tier
    if state.get("street") != "preflop":
        key["miss_reason"] = "street_not_preflop_p0"
        return key
    raises = [h for h in state.get("history") or [] if h.get("action") in ("raise", "allin")]
    if len(raises) == 0:
        key["line"] = "rfi"
        key["vs_pos"] = None
    elif len(raises) == 1:
        key["line"] = "vs_open"
        key["vs_pos"] = seat_position(btn, raises[0]["seat"], n)
    else:
        key["miss_reason"] = "line_unsupported"
        return key
    key["spot_id"] = f"6max_{tier}bb_{key['hero_pos'].lower()}_{key['line']}"
    if key["line"] == "vs_open" and key.get("vs_pos"):
        key["spot_id"] = f"6max_{tier}bb_{key['hero_pos'].lower()}_vs_{key['vs_pos'].lower()}_open"
    return key


def charts_root_default() -> Path:
    local = Path(".nlhe/charts")
    if local.is_dir():
        return local.resolve()
    workspace = Path.cwd() / "nlhe/charts"
    if workspace.is_dir():
        return workspace.resolve()
    return (Path.home() / ".cursor/skills/nlhe/charts").resolve()


def _lookup_miss(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "hit": False,
        "reason": reason,
        "freqs": None,
        "actions": None,
        "pack_id": None,
        "spot_id": extra.get("spot_id"),
        "meta": extra.get("meta"),
    }


def lookup_chart(charts_root: Path, key: dict[str, Any]) -> dict[str, Any]:
    if key.get("miss_reason"):
        return _lookup_miss(key["miss_reason"])

    spot_id = key.get("spot_id")
    hand = key.get("hero_hand")
    if not spot_id or not hand:
        return _lookup_miss("incomplete_key")

    manifest_path = charts_root / "manifest.json"
    if not manifest_path.is_file():
        return _lookup_miss("spot_file_missing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    path: Path | None = None
    pack_id: str | None = None
    meta: dict[str, Any] = {}
    for pack in manifest.get("packs") or []:
        pack_path = pack.get("path")
        if not pack_path:
            continue
        cand = charts_root / pack_path / "spots" / f"{spot_id}.json"
        if cand.is_file():
            path = cand
            pack_id = pack.get("id")
            meta_path = charts_root / pack_path / "meta.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            break

    if path is None:
        return _lookup_miss("spot_file_missing")

    data = json.loads(path.read_text(encoding="utf-8"))
    freqs = (data.get("combos") or {}).get(hand)
    if not freqs:
        return _lookup_miss("combo_not_in_chart", spot_id=spot_id, meta=meta)

    total = sum(freqs.values())
    if abs(total - 1.0) > 0.01:
        return _lookup_miss("invalid_freqs", meta=meta)

    return {
        "hit": True,
        "reason": None,
        "freqs": freqs,
        "actions": data.get("actions"),
        "pack_id": pack_id or meta.get("id"),
        "spot_id": spot_id,
        "meta": meta,
        "pack": meta.get("id"),
        "source": meta.get("source"),
    }


def _full_deck() -> list[str]:
    return [r + s for r in RANKS for s in SUITS]


def suggest_action(freqs: dict[str, float]) -> str:
    return max(freqs.items(), key=lambda kv: kv[1])[0]


def estimate_equity(
    hole: list[str],
    board: list[str],
    n_opponents: int,
    trials: int = 200,
    eval_fn: Callable[[list[str], list[str]], tuple] | None = None,
    rng: random.Random | None = None,
) -> Optional[float]:
    """Uniform random opponent holes + runout; ties split 1/n winners."""
    if eval_fn is None or len(hole) != 2:
        return None
    n_opponents = max(1, n_opponents)
    rng = rng or random.Random()
    known = set(hole + list(board or []))
    deck = [c for c in _full_deck() if c not in known]
    need_board = max(0, 5 - len(board or []))
    if len(deck) < n_opponents * 2 + need_board:
        return None

    wins = 0.0
    work = list(deck)
    full_board = list(board or [])
    for _ in range(trials):
        rng.shuffle(work)
        idx = 0
        opp_holes: list[list[str]] = []
        for _ in range(n_opponents):
            opp_holes.append([work[idx], work[idx + 1]])
            idx += 2
        runout = full_board + work[idx : idx + need_board]
        hero_score = eval_fn(hole, runout)
        all_scores = [hero_score] + [eval_fn(oh, runout) for oh in opp_holes]
        best_score = max(all_scores)
        if hero_score == best_score:
            winners = sum(1 for s in all_scores if s == best_score)
            wins += 1.0 / winners
    return wins / trials


def render_coach_block(
    state: dict[str, Any],
    charts_root: Optional[Path] = None,
    eval_fn: Callable[[list[str], list[str]], tuple] | None = None,
) -> str:
    if state.get("status") != "awaiting_human":
        return ""
    root = charts_root or charts_root_default()
    hero = next(p for p in state["players"] if p.get("is_human"))
    mb = max(p["bet"] for p in state["players"] if not p["folded"])
    to_call = mb - hero["bet"]
    pot = state["pot"] + sum(p["bet"] for p in state["players"])
    odds = pot_odds_needed(pot, to_call)
    n_opp = len([p for p in state["players"] if not p["folded"] and not p["is_human"]])
    eq = estimate_equity(hero["hole"], state.get("board") or [], max(1, n_opp), eval_fn=eval_fn)
    key = build_spot_key(state)
    hit = lookup_chart(root, key)
    lines = ["── GTO 教练 ──"]
    if odds is None:
        lines.append("Pot odds: （无需跟注）")
    else:
        lines.append(f"Pot odds: 跟注需 {odds * 100:.0f}%")
    if eq is not None:
        lines.append(f"Equity≈{eq * 100:.0f}%（MC，非 GTO）")
    if hit["hit"]:
        freq_s = " ".join(
            f"{a} {v * 100:.0f}%" for a, v in sorted(hit["freqs"].items(), key=lambda x: -x[1])
        )
        lines.append(
            f"Chart: {hit.get('pack')} / {hit.get('spot_id')} · {key.get('hero_hand')} [{hit.get('source')}]"
        )
        lines.append(f"GTO: {freq_s}")
        lines.append(f"建议: {suggest_action(hit['freqs'])}（谱命中）")
    else:
        reason = hit.get("reason") or key.get("miss_reason") or "unknown"
        lines.append(f"Chart: NO_CHART（原因: {reason}）")
        lines.append("建议: （无谱，不提供 GTO 行动）")
    return "\n".join(lines)


def build_coach_log_entry(
    state: dict[str, Any],
    charts_root: Optional[Path] = None,
    eval_fn: Callable[[list[str], list[str]], tuple] | None = None,
) -> dict[str, Any]:
    """Build one coach_log snapshot for the current hero decision point."""
    root = charts_root or charts_root_default()
    hero = next(p for p in state["players"] if p.get("is_human"))
    mb = max(p["bet"] for p in state["players"] if not p.get("folded"))
    to_call = mb - hero["bet"]
    pot = state["pot"] + sum(p["bet"] for p in state["players"])
    odds = pot_odds_needed(pot, to_call)
    n_opp = len([p for p in state["players"] if not p.get("folded") and not p.get("is_human")])
    eq = estimate_equity(
        hero["hole"], state.get("board") or [], max(1, n_opp), eval_fn=eval_fn
    )
    key = build_spot_key(state)
    hit = lookup_chart(root, key)
    suggested = suggest_action(hit["freqs"]) if hit["hit"] and hit.get("freqs") else None
    return {
        "hand_id": state.get("hand_id"),
        "street": state.get("street"),
        "to_act": state.get("to_act"),
        "hero_hand": key.get("hero_hand"),
        "spot_id": key.get("spot_id"),
        "hit": hit["hit"],
        "freqs": hit.get("freqs"),
        "pot_odds": odds,
        "equity": eq,
        "suggested": suggested,
        "hero_action": None,
    }


def sync_coach_log(
    state: dict[str, Any],
    charts_root: Optional[Path] = None,
    eval_fn: Callable[[list[str], list[str]], tuple] | None = None,
) -> bool:
    """Append coach_log once per hero decision (awaiting_human). Returns True if appended."""
    if state.get("status") != "awaiting_human":
        return False
    to_act = state.get("to_act")
    hand_id = state.get("hand_id")
    street = state.get("street")
    log = state.setdefault("coach_log", [])
    if log:
        last = log[-1]
        if (
            last.get("hero_action") is None
            and last.get("to_act") == to_act
            and last.get("street") == street
            and last.get("hand_id") == hand_id
        ):
            return False
    log.append(build_coach_log_entry(state, charts_root=charts_root, eval_fn=eval_fn))
    return True


def set_hero_action_on_log(state: dict[str, Any], seat: int, action: str) -> None:
    """Record hero's chosen action on the pending coach_log entry for this seat."""
    for entry in reversed(state.get("coach_log") or []):
        if (
            entry.get("hero_action") is None
            and entry.get("hand_id") == state.get("hand_id")
            and entry.get("to_act") == seat
        ):
            entry["hero_action"] = action
            return


def format_review_line(
    street: str,
    hand: str,
    hero_action: str,
    freqs: dict[str, float],
) -> str:
    """Format one review line; mark 谱外 when hero_action is not the max-freq GTO action."""
    suggested = suggest_action(freqs)
    freq_s = " ".join(
        f"{a} {v * 100:.0f}%" for a, v in sorted(freqs.items(), key=lambda x: -x[1])
    )
    line = f"{street} {hand}: 你 {hero_action} | GTO {freq_s}"
    if hero_action != suggested:
        line += " 【谱外】"
    return line


def render_charts_list(charts_root: Path) -> str:
    """List installed chart packs from manifest + meta assumptions."""
    lines = ["── Charts ──"]
    manifest_path = charts_root / "manifest.json"
    if not manifest_path.is_file():
        lines.append("（无 manifest）")
        return "\n".join(lines)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    packs = manifest.get("packs") or []
    if not packs:
        lines.append("（manifest 中无 pack）")
        return "\n".join(lines)
    for pack in packs:
        pack_id = pack.get("id") or "?"
        pack_path = pack.get("path")
        version = pack.get("version") or "?"
        lines.append(f"· {pack_id} v{version}")
        meta: dict[str, Any] = {}
        if pack_path:
            meta_path = charts_root / pack_path / "meta.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("source"):
            lines.append(f"  source: {meta['source']}")
        assumptions = meta.get("assumptions") or {}
        if assumptions:
            parts = ", ".join(f"{k}={v}" for k, v in assumptions.items())
            lines.append(f"  assumptions: {parts}")
        if meta.get("notes"):
            lines.append(f"  notes: {meta['notes']}")
    return "\n".join(lines)


def render_review(state: dict[str, Any], god: bool = False) -> str:
    """Print review lines from state coach_log."""
    lines = ["── GTO Review ──"]
    log = state.get("coach_log") or []
    shown = 0
    for entry in log:
        hero_action = entry.get("hero_action")
        if hero_action is None:
            continue
        street = entry.get("street") or "?"
        hand = entry.get("hero_hand") or "?"
        freqs = entry.get("freqs")
        if freqs and entry.get("hit"):
            lines.append(format_review_line(street, hand, hero_action, freqs))
        else:
            reason = entry.get("spot_id") or "NO_CHART"
            lines.append(f"{street} {hand}: 你 {hero_action} | Chart: NO_CHART ({reason})")
        shown += 1
    if shown == 0:
        lines.append("（暂无 Hero 决策记录）")
    if god:
        hero = next((p for p in state["players"] if p.get("is_human")), None)
        if hero and hero.get("hole"):
            hole_s = " ".join(hero["hole"])
            lines.append(f"God: Hero holes = {hole_s}")
    return "\n".join(lines)

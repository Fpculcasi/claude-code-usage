#!/usr/bin/env python3
"""
claude_usage_summary.py — Riassume consumi Claude Code cross-session.
Legge i file JSONL in ~/.claude/projects/ (Windows/macOS/Linux).
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# --- CONFIGURAZIONE PRICING (USD per 1M token) ---
# Fonte: https://docs.anthropic.com/en/docs/about-claude/pricing
PRICING = {
    "claude-opus-4-7":   {"input": 5.00,  "output": 25.00, "cache_write_5m": 6.25,  "cache_write_1h": 10.00, "cache_read": 0.50},
    "claude-opus-4-6":   {"input": 5.00,  "output": 25.00, "cache_write_5m": 6.25,  "cache_write_1h": 10.00, "cache_read": 0.50},
    "claude-opus-4-5":   {"input": 5.00,  "output": 25.00, "cache_write_5m": 6.25,  "cache_write_1h": 10.00, "cache_read": 0.50},
    "claude-opus-4-1":   {"input": 15.00, "output": 75.00, "cache_write_5m": 18.75, "cache_write_1h": 30.00, "cache_read": 1.50},
    "claude-opus-4":     {"input": 15.00, "output": 75.00, "cache_write_5m": 18.75, "cache_write_1h": 30.00, "cache_read": 1.50},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "cache_write_5m": 3.75,  "cache_write_1h": 6.00,  "cache_read": 0.30},
    "claude-sonnet-4-5": {"input": 3.00,  "output": 15.00, "cache_write_5m": 3.75,  "cache_write_1h": 6.00,  "cache_read": 0.30},
    "claude-sonnet-4":   {"input": 3.00,  "output": 15.00, "cache_write_5m": 3.75,  "cache_write_1h": 6.00,  "cache_read": 0.30},
    "claude-haiku-4-5":  {"input": 1.00,  "output": 5.00,  "cache_write_5m": 1.25,  "cache_write_1h": 2.00,  "cache_read": 0.10},
    "claude-haiku-3-5":  {"input": 0.80,  "output": 4.00,  "cache_write_5m": 1.00,  "cache_write_1h": 1.60,  "cache_read": 0.08},
    # fallback
    "default":           {"input": 3.00,  "output": 15.00, "cache_write_5m": 3.75,  "cache_write_1h": 6.00,  "cache_read": 0.30},
}
EUR_USD_RATE = 0.92

def get_pricing(model: str) -> dict:
    for key in PRICING:
        if key == "default":
            continue
        if key in model:
            return PRICING[key]
    return PRICING["default"]

def find_jsonl_files():
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        print(f"⚠️  Directory non trovata: {base}")
        sys.exit(1)
    files = list(base.rglob("*.jsonl"))
    return sorted(files)

def parse_session(filepath: Path):
    """Parsa un file JSONL, deduplicando per requestId."""
    seen_requests = {}
    session_id = None
    model = "unknown"
    ts_start = None
    ts_end = None
    title = None
    num_turns = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Titolo sessione
            if entry.get("type") == "ai-title" and entry.get("aiTitle"):
                title = entry["aiTitle"]

            # Session ID
            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]

            # Solo entry assistant con message.usage
            if entry.get("type") != "assistant":
                continue

            message = entry.get("message", {})
            usage = message.get("usage")
            if not usage:
                continue

            req_id = entry.get("requestId", "")
            # Deduplicazione: stesso requestId = stessa API call
            if req_id and req_id in seen_requests:
                continue
            if req_id:
                seen_requests[req_id] = usage

            # Modello
            if message.get("model"):
                model = message["model"]

            # Timestamp
            ts = entry.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if ts_start is None or dt < ts_start:
                        ts_start = dt
                    if ts_end is None or dt > ts_end:
                        ts_end = dt
                except (ValueError, TypeError):
                    pass

            num_turns += 1

    # Aggrega token
    total_input = 0
    total_output = 0
    total_cache_write_5m = 0
    total_cache_write_1h = 0
    total_cache_read = 0

    for usage in seen_requests.values():
        total_input += usage.get("input_tokens", 0)
        total_output += usage.get("output_tokens", 0)
        total_cache_read += usage.get("cache_read_input_tokens", 0)

        # Distingui 5m vs 1h cache write
        cache_creation = usage.get("cache_creation", {})
        if cache_creation:
            total_cache_write_5m += cache_creation.get("ephemeral_5m_input_tokens", 0)
            total_cache_write_1h += cache_creation.get("ephemeral_1h_input_tokens", 0)
        else:
            # fallback: tutto come 5m
            total_cache_write_5m += usage.get("cache_creation_input_tokens", 0)

    # Calcolo costo
    p = get_pricing(model)
    cost_usd = (
        (total_input * p["input"] / 1_000_000) +
        (total_output * p["output"] / 1_000_000) +
        (total_cache_write_5m * p["cache_write_5m"] / 1_000_000) +
        (total_cache_write_1h * p["cache_write_1h"] / 1_000_000) +
        (total_cache_read * p["cache_read"] / 1_000_000)
    )

    total_cache_write = total_cache_write_5m + total_cache_write_1h

    return {
        "file": str(filepath.name),
        "project": filepath.parent.name,
        "session_id": session_id or filepath.stem[:12],
        "title": title or "(senza titolo)",
        "model": model,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cache_write": total_cache_write,
        "cache_read": total_cache_read,
        "total_tokens": total_input + total_output + total_cache_write + total_cache_read,
        "cost_usd": cost_usd,
        "cost_eur": cost_usd * EUR_USD_RATE,
        "turns": num_turns,
        "api_calls": len(seen_requests),
        "start": ts_start,
        "end": ts_end,
    }

def format_table(sessions):
    sessions = [s for s in sessions if s["total_tokens"] > 0]

    if not sessions:
        print("⚠️  Nessun dato di usage trovato nei file JSONL.")
        return

    # Raggruppa per progetto
    from collections import defaultdict
    projects = defaultdict(list)
    for s in sessions:
        projects[s["project"]].append(s)

    # Totali globali
    tot_in = tot_out = tot_cw = tot_cr = 0
    tot_usd = tot_eur = 0.0
    all_calls = 0

    print("\n" + "=" * 130)

    for project_name in sorted(projects.keys()):
        project_sessions = projects[project_name]
        proj_in = proj_out = proj_cw = proj_cr = 0
        proj_usd = proj_eur = 0.0
        proj_calls = 0

        # Intestazione del progetto
        print(f"📁 {project_name}")
        print(f"{'TITOLO':<40} {'MODELLO':<18} {'INPUT':>9} {'OUTPUT':>9} "
              f"{'CACHE W':>9} {'CACHE R':>9} {'USD':>9} {'EUR':>9} {'CALLS':>6}")
        print("-" * 130)

        for s in project_sessions:
            title = s["title"][:39]
            model_short = s["model"][:17]

            print(f"  {title:<38} {model_short:<18} {s['input_tokens']:>9,} {s['output_tokens']:>9,} "
                  f"{s['cache_write']:>9,} {s['cache_read']:>9,} "
                  f"${s['cost_usd']:>8.4f} €{s['cost_eur']:>8.4f} "
                  f"{s['api_calls']:>6}")

            proj_in += s["input_tokens"]
            proj_out += s["output_tokens"]
            proj_cw += s["cache_write"]
            proj_cr += s["cache_read"]
            proj_usd += s["cost_usd"]
            proj_eur += s["cost_eur"]
            proj_calls += s["api_calls"]

        print(f"{'└─ SUBTOTALE':<40} {'':<18} {proj_in:>9,} {proj_out:>9,} "
              f"{proj_cw:>9,} {proj_cr:>9,} "
              f"${proj_usd:>8.4f} €{proj_eur:>8.4f} "
              f"{proj_calls:>6}")
        print("=" * 130)

        tot_in += proj_in
        tot_out += proj_out
        tot_cw += proj_cw
        tot_cr += proj_cr
        tot_usd += proj_usd
        tot_eur += proj_eur
        all_calls += proj_calls

    print(f"\n{'TOTALE GENERALE':<40} {'':<18} {tot_in:>9,} {tot_out:>9,} "
          f"{tot_cw:>9,} {tot_cr:>9,} "
          f"${tot_usd:>8.4f} €{tot_eur:>8.4f} "
          f"{all_calls:>6}")
    print("=" * 130)

    print(f"\n📊 Sessioni: {len(sessions)}")
    print(f"💰 Costo totale: ${tot_usd:.4f} / €{tot_eur:.4f}")
    print(f"🔤 Token totali: {tot_in + tot_out + tot_cw + tot_cr:,}")
    print(f"   ├─ Input:        {tot_in:>12,}")
    print(f"   ├─ Output:       {tot_out:>12,}")
    print(f"   ├─ Cache write:  {tot_cw:>12,}")
    print(f"   └─ Cache read:   {tot_cr:>12,}\n")

def main():
    print("🔍 Ricerca file JSONL in:", Path.home() / ".claude" / "projects")
    files = find_jsonl_files()
    print(f"   Trovati {len(files)} file\n")

    sessions = []
    for f in files:
        try:
            sessions.append(parse_session(f))
        except Exception as e:
            print(f"   ⚠️  Errore: {f.name}: {e}")

    sessions.sort(key=lambda s: s["start"] or datetime.min.replace(tzinfo=timezone.utc))
    format_table(sessions)

if __name__ == "__main__":
    main()
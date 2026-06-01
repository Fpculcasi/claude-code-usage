# Claude Usage Summary

## Why

Track actual token consumption and costs across Claude Code sessions. The script aggregates data from project JSONL files, deduplicates by requestId, and calculates costs in USD/EUR using official Anthropic pricing.

---

## How It Works

The script scans all JSONL files in `~/.claude/projects/` (cross-platform: Windows, macOS, Linux) and:

1. **Reads sessions**: Extracts `assistant` entries with usage metrics (tokens consumed)
2. **Deduplicates**: Groups by `requestId` to avoid double-counting (e.g., on retries)
3. **Extracts metadata**: Captures session title, model used, start/end timestamps
4. **Separates cache types**: Distinguishes ephemeral 5m and 1h (cache write) vs cache read
5. **Calculates costs**: Applies official Anthropic pricing for input, output, cache operations
6. **Groups by project**: Organizes sessions by project folder (parent directory name)
7. **Displays results**: Hierarchical table grouped by project with per-project subtotals + global total

### Example Output

```
📁 project-1
TITOLO                                   MODELLO            INPUT    OUTPUT  CACHE W  CACHE R      USD      EUR  CALLS
  Debug API integration                  claude-sonnet-4-6  45,280    12,450   20,000    5,200  $0.3241  €0.2981     12
  Add feature to dashboard               claude-haiku-4-5   12,100     3,200        0        0  $0.0141  €0.0130      4
└─ SUBTOTALE                                                 57,380    15,650   20,000    5,200  $0.3382  €0.3111     16
==================================================

📁 project-2
TITOLO                                   MODELLO            INPUT    OUTPUT  CACHE W  CACHE R      USD      EUR  CALLS
  Refactor auth module                   claude-opus-4-8   128,900    35,600        0        0  $1.2845  €1.1817      8
└─ SUBTOTALE                                                128,900    35,600        0        0  $1.2845  €1.1817      8
==================================================

TOTALE GENERALE                                             186,280    51,250   20,000    5,200  $1.6227  €1.4929     24

📊 Sessions: 3
💰 Total cost: $1.6227 / €1.4929
🔤 Total tokens: 262,730
   ├─ Input:             186,280
   ├─ Output:             51,250
   ├─ Cache write:        20,000
   └─ Cache read:          5,200
```

### Supported Pricing

The script includes official rates for:
- **Opus** (4.8, 4.7, 4.6, 4.5, 4.1, 4)
- **Sonnet** (4.6, 4.5, 4)
- **Haiku** (4.5, 3.5)

Automatic fallback to Sonnet pricing for unrecognized models.

---

## Requirements

- Python 3.7+
- No external dependencies

## Usage

```bash
python3 claude_usage_summary.py
```

The script is read-only: it examines session logs without modifying them.

---

## Notes

- **Deduplication**: Same `requestId` = same API call (counted once)
- **Global timestamps**: Records session start/end times
- **Currency conversion**: Fixed rate of 1 USD = 0.92 EUR
- **Resilient parsing**: Malformed JSON in JSONL is silently skipped

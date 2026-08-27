# claude-code-usage

A zero-dependency Python script that summarizes token consumption and USD/EUR costs across all your Claude Code sessions.

```
python claude_usage_summary.py
```

## What it does

Reads the JSONL session logs stored in `~/.claude/projects/`, deduplicates entries by request ID, and prints a hierarchical cost breakdown grouped by project folder.

```
project-foo/
  claude-sonnet-4-5   input: 12 400   output: 3 200   cache_write: 8 100   cache_read: 41 000   $0.84
  ...
  subtotal                                                                                        $1.12

TOTAL                                                                                             $4.37  (€4.02)
```

## Details

- Separates cache-write vs cache-read tokens and applies Anthropic's official per-model rates
- Fixed USD→EUR rate (1 USD = 0.92 EUR)
- Works on Windows, macOS, and Linux
- Read-only — never modifies the original logs
- Gracefully skips malformed JSONL entries

## Requirements

Python 3.7+ — standard library only, no `pip install` needed.

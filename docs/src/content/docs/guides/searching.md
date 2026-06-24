---
title: Searching flights
description: The search, dates, multi, and airports commands and their flags.
---

All gfly commands are **reads** — it searches, it never books.

## `search` — one-way / round-trip

```bash
gfly search <FROM> <TO> --depart YYYY-MM-DD [--return YYYY-MM-DD] [flags]
```

| Flag | Values (default) | Notes |
|---|---|---|
| `--depart` | `YYYY-MM-DD` | required |
| `--return` | `YYYY-MM-DD` | omit for one-way |
| `--cabin` | `economy` (def) · `premium` · `business` · `first` | |
| `--stops` | `any` (def) · `nonstop` · `1` | |
| `--sort` | `best` (def) · `price` · `duration` | applied after fetch |
| `--adults` / `--children` / `--infants` | ints (1/0/0) | validated early |
| `--currency` | ISO code (`USD`) | also `GFLY_CURRENCY` |

Airport codes are case-insensitive (`jfk` → `JFK`). Bad dates fail fast as a `USAGE` error before any
network call.

## `dates` — cheapest price per day

```bash
gfly dates <FROM> <TO> --depart-range 2026-08-01..2026-08-10
```

No upstream exposes a date grid, so gfly scans **one search per day**. On the `google` backend it
paces these politely (one per `--min-interval`); a wide window can take minutes. A late
[block](/guides/rate-limits/) returns the days gathered so far with `partial: true`.

## `multi` — multi-city

```bash
gfly multi --leg FROM:TO:DATE --leg FROM:TO:DATE [...]
```

Needs ≥2 legs; **google backend only**. Accepts the same `--cabin` / `--stops` / passenger flags.

## `airports search` — resolve IATA codes

```bash
gfly airports search "tokyo"
```

Offline lookup over ~7.9k airports (the `airportsdata` dataset). Use it so an agent never guesses a
code. Returns `iata`, `name`, `city`, `country`.

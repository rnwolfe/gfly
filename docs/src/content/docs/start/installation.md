---
title: Installation
description: Install gfly via uv, uvx, pipx, or pip. Requires Python 3.10+.
---

`gfly` is a Python package. The default `google` backend needs **no API key and no account** — just
install and run.

## Zero-install trial

```bash
uvx gfly search JFK LHR --depart 2026-08-15
```

`uvx` runs gfly in a disposable environment — nothing is installed.

## Install

| Method | Command |
|---|---|
| **uv** (recommended) | `uv tool install gfly` |
| **pipx** | `pipx install gfly` |
| **pip** | `pip install gfly` |

Requires **Python ≥ 3.10**. gfly ships the `fast-flights` engine (google backend) plus offline IATA
data; the [`serpapi` backend](/guides/backends/) needs no extra dependency.

## Verify

```bash
gfly --version
gfly doctor      # checks auth, keyring, connectivity, throttle state
gfly schema      # machine-readable command tree + exit codes
```

## Supply-chain verification

Release artifacts carry a `SHA256SUMS` file and a build-provenance attestation:

```bash
gh attestation verify gfly-<version>-py3-none-any.whl --repo rnwolfe/gfly
```

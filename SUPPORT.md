# Support

Need help with `gfly`?

1. **Built-in self-help** — fastest:
   - `gfly --help` / `gfly <command> --help` — example-led help.
   - `gfly doctor --json` — checks auth, keyring, connectivity, and throttle state.
   - `gfly agent` — the full usage contract embedded in the binary.
   - `gfly schema` — command tree, flags, exit codes, env vars.
2. **Docs** — see the README and the documentation site.
3. **Questions / ideas** — open a [GitHub Discussion](https://github.com/rnwolfe/gfly/discussions).
4. **Bugs** — open an [issue](https://github.com/rnwolfe/gfly/issues/new/choose) (the form asks for
   `gfly --version`, OS, backend, and the structured error).
5. **Security** — do **not** use public issues; see [SECURITY.md](SECURITY.md).

**Common gotchas**

- Getting exit `20` (`BLOCKED`) or `21` (`SCHEMA_DRIFT`)? The default `google` backend is
  reverse-engineered — back off (the throttle tells you `retryAfterSeconds`), try `--proxy`, or switch
  `--backend serpapi`.
- `dates` is slow? It runs one search per day — use a small `--depart-range`.

This is a community project maintained on a best-effort basis. No SLA.

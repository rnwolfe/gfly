# gfly demo — split-flap departure-board theme.
# All commands are OFFLINE/deterministic (help, schema, airports, validation, agent)
# so the GIF never hangs on a live Google connection. Regenerate: `vhs demo/gfly.tape`.

Output demo/gfly.gif

Set Shell      "bash"
Set FontSize   18
Set Width      1200
Set Height     780
Set Padding    24
Set TypingSpeed 32ms
Set Theme { "name": "gfly-split-flap", "background": "#0B0E13", "foreground": "#F5B70A", "cursor": "#F5B70A", "selection": "#26303B", "black": "#0B0E13", "red": "#E74C3C", "green": "#2ECC71", "yellow": "#F5B70A", "blue": "#5AA9E6", "magenta": "#C792EA", "cyan": "#56C2C2", "white": "#D7DCE2", "brightBlack": "#6B7280", "brightRed": "#FF6B5E", "brightGreen": "#56E08A", "brightYellow": "#FFD24A", "brightBlue": "#82C4FF", "brightMagenta": "#E0B0FF", "brightCyan": "#7FE3E3", "brightWhite": "#FFFFFF" }

# keep the demo offline + fast, no color codes fighting the theme
Hide
Type "export GFLY_NO_THROTTLE=1 NO_COLOR=1 PS1='\033[38;5;179m✈ \033[0m'"  Enter
Type "clear"  Enter
Show

Sleep 600ms
Type "gfly --help"  Enter
Sleep 2.6s

Type "clear"  Enter
# zero-auth: resolve an airport offline, no key, no account
Type "gfly airports search tokyo --limit 3"  Enter
Sleep 2.6s

Type "clear"  Enter
# machine-readable self-description: exit codes + live safety/throttle state
Type "gfly schema | jq '{commands: .commands.commands|keys, exit_codes, safety}'"  Enter
Sleep 3.2s

Type "clear"  Enter
# fail-fast validation — a usage error, not a wasted upstream call
Type "gfly search JFK LHR --depart 08/01/2026; echo exit=$?"  Enter
Sleep 2.6s

Type "clear"  Enter
# the agent contract is embedded in the binary
Type "gfly agent | head -8"  Enter
Sleep 2.8s

Sleep 1.2s

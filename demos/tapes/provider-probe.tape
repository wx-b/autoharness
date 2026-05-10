Output demos/output/provider-probe.gif
Output demos/output/provider-probe.mp4
Output demos/output/provider-probe.webm

Require uv
Require jq

Set Shell "bash"
Set FontFamily "MesloLGS Nerd Font Mono"
Set FontSize 17
Set Width 1100
Set Height 640
Set LetterSpacing 0
Set LineHeight 1.15
Set Padding 30
Set Framerate 24
Set TypingSpeed 72ms
Set Theme { "name": "GitHub Dark", "black": "#484f58", "red": "#ff7b72", "green": "#3fb950", "yellow": "#d29922", "blue": "#58a6ff", "magenta": "#bc8cff", "cyan": "#39c5cf", "white": "#b1bac4", "brightBlack": "#6e7681", "brightRed": "#ffa198", "brightGreen": "#56d364", "brightYellow": "#e3b341", "brightBlue": "#79c0ff", "brightMagenta": "#d2a8ff", "brightCyan": "#56d4dd", "brightWhite": "#f0f6fc", "background": "#0d1117", "foreground": "#e6edf3", "selection": "#264f78", "cursor": "#e6edf3" }
Set WindowBar "Colorful"
Set WindowBarSize 36
Set BorderRadius 10
Set Margin 24
Set MarginFill "#11111b"

Hide
Type "set -e"
Enter
Type "export DEMO_ROOT=$(mktemp -d /tmp/autoharness-demo.XXXXXX)"
Enter
Type "export AUTOHARNESS_DEMO_SOURCE=${AUTOHARNESS_DEMO_SOURCE:-$PWD}"
Enter
Type "cd $AUTOHARNESS_DEMO_SOURCE"
Enter
Type "export PS1='\[\e[38;5;39m\]autoharness\[\e[0m\] \[\e[38;5;244m\]>\[\e[0m\] '"
Enter
Type "uv sync --extra dev --extra preflight >/dev/null 2>&1"
Enter
Type "clear"
Enter
Show

Type@76ms "uv run autoharness provider-probe"
Sleep 110ms
Type@48ms " --manifest manifests/provider_probe_model_preflight_free.yaml"
Sleep 110ms
Type@50ms " --artifact-root $DEMO_ROOT/provider/probe"
Sleep 90ms
Type@48ms " --dry-run"
Enter
Sleep 1s

Type@70ms "jq -C '{status, dry_run, provider, model, auth_kind, max_spend_usd, actual_spend_usd, messages}'"
Sleep 100ms
Type@48ms " $DEMO_ROOT/provider/probe/provider-probe-summary.json"
Enter
Sleep 1s

Type@76ms "uv run autoharness provider-report"
Sleep 100ms
Type@48ms " --probe-root $DEMO_ROOT/provider/probe"
Sleep 100ms
Type@48ms " --output-root $DEMO_ROOT/provider/report"
Enter
Sleep 2s

Type@72ms "ls $DEMO_ROOT/provider/report"
Enter
Sleep 1s

Hide
Type "rm -rf $DEMO_ROOT"
Enter
Show

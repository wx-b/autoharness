Output demos/output/quickstart.gif
Output demos/output/quickstart.mp4
Output demos/output/quickstart.webm

Require uv

Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 17
Set Width 1100
Set Height 640
Set LetterSpacing 0
Set LineHeight 1.15
Set Padding 30
Set Framerate 24
Set TypingSpeed 78ms
Set Theme { "name": "GitHub Dark", "black": "#484f58", "red": "#ff7b72", "green": "#3fb950", "yellow": "#d29922", "blue": "#58a6ff", "magenta": "#bc8cff", "cyan": "#39c5cf", "white": "#b1bac4", "brightBlack": "#6e7681", "brightRed": "#ffa198", "brightGreen": "#56d364", "brightYellow": "#e3b341", "brightBlue": "#79c0ff", "brightMagenta": "#d2a8ff", "brightCyan": "#56d4dd", "brightWhite": "#f0f6fc", "background": "#0d1117", "foreground": "#e6edf3", "selection": "#264f78", "cursor": "#e6edf3" }
Set WindowBar "Colorful"
Set WindowBarSize 36
Set BorderRadius 10
Set Margin 24
Set MarginFill "#11111b"

Hide
Type "set -e"
Enter
Type "export AUTOHARNESS_DEMO_SOURCE=${AUTOHARNESS_DEMO_SOURCE:-$PWD}"
Enter
Type "cd $AUTOHARNESS_DEMO_SOURCE"
Enter
Type "uv sync --extra dev >/dev/null 2>&1"
Enter
Type "export AUTOHARNESS_RUN_ID=demo-run"
Enter
Type "rm -rf /tmp/autoharness-demo"
Enter
Type "clear"
Enter
Show

Type@88ms "OUT"
Sleep 90ms
Type@55ms "="
Sleep 70ms
Type@72ms "/tmp/autoharness-demo"
Enter
Sleep 500ms

Type@84ms "uv"
Sleep 90ms
Type@58ms " run"
Sleep 130ms
Type@78ms " autoharness"
Sleep 120ms
Type@80ms " verify"
Sleep 170ms
Type@48ms " --manifest"
Sleep 90ms
Type@82ms " manifests/offline_smoke.yaml"
Sleep 160ms
Type@50ms " --artifact-root"
Sleep 90ms
Type@78ms " $OUT/verify"
Enter
Sleep 1.2s

Type@74ms "ls"
Sleep 120ms
Type@80ms " $OUT/verify"
Enter
Sleep 1.8s

Hide
Type "rm -rf /tmp/autoharness-demo"
Enter
Show

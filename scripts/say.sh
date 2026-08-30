#!/bin/bash
# Lint one herdr message, then deliver it without rewriting its bytes.

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <pane> <message>" >&2
    exit 64
fi

pane=$1
message=$2
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
lint_py="$script_dir/lint_wait_claim.py"
lint_out=$(mktemp "${TMPDIR:-/tmp}/herdr-lint.XXXXXX") || exit 70
send_out=$(mktemp "${TMPDIR:-/tmp}/herdr-send-out.XXXXXX") || exit 70
send_err=$(mktemp "${TMPDIR:-/tmp}/herdr-send-err.XXXXXX") || exit 70
# shellcheck disable=SC2329  # invoked by trap
cleanup() { rm -f "$lint_out" "$send_out" "$send_err"; }
trap cleanup EXIT HUP INT TERM

printf '%s' "$message" | python3 "$lint_py" >"$lint_out" 2>&1
lint_rc=$?
lint_broken=false
if [ "$lint_rc" -eq 1 ]; then
    while IFS= read -r violation; do
        [ -n "$violation" ] && printf '擋下：%s\n' "$violation"
    done <"$lint_out"
    cat <<'EOF'
這句說你在等，但同句或下一句沒有會叫醒你的東西。改成下面任一種再送：

 1) 掛了就寫把手（同句或下一句）：
    「等 pi 的量測數字；背景 until 已掛 bf9df30it」
    「等 pi 的量測數字；Monitor be59l03eh 盯著」
    「等 pi 的量測數字；ScheduleWakeup 已排」
 2) 先答：「我手上哪一行需要對方的輸出？」答不出具體哪一行 → 不用等，把事做完再送。
 3) 等的是額度／授權？「這件事任何人有額度都能做：指令是 X、預期是 Y」
 4) 其實已經做完了？「X 做完了，產物在 Y」
 5) 這句不是在等？提字只用引號包「等」這個字；轉述請加把手或改寫。
EOF
    exit 1
elif [ "$lint_rc" -ne 0 ]; then
    lint_broken=true
    echo "警告：lint 故障，本則未檢查；仍嘗試送出。" >&2
    cat "$lint_out" >&2
fi

# Prefer coreutils timeout when present; macOS/Bash 3.2 gets an equivalent watchdog.
if command -v timeout >/dev/null 2>&1; then
    timeout 20 herdr agent prompt "$pane" "$message" >"$send_out" 2>"$send_err"
elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout 20 herdr agent prompt "$pane" "$message" >"$send_out" 2>"$send_err"
else
    herdr agent prompt "$pane" "$message" >"$send_out" 2>"$send_err" &
    child=$!
    (sleep 20; kill -TERM "$child" 2>/dev/null) &
    watchdog=$!
    wait "$child" 2>/dev/null
    kill "$watchdog" 2>/dev/null
    wait "$watchdog" 2>/dev/null
fi

# Herdr versions disagree on exit codes; only this response type proves delivery.
if grep -Fq '"type":"agent_prompted"' "$send_out"; then
    cat "$send_out"
    cat "$send_err" >&2
    printf 'sent → %s\n' "$pane" >&2
    [ "$lint_broken" = true ] && exit 3
    exit 0
fi

cat "$send_out" >&2
cat "$send_err" >&2
echo "未送出：herdr 未回傳 agent_prompted（含逾時或 pane 不存在）。" >&2
exit 2

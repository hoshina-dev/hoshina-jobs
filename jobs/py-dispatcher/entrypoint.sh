#!/bin/sh
set -e

LOG_FILE="/tmp/job.log"
STDOUT_FILE="/tmp/py_stdout"
STDERR_FILE="/tmp/py_stderr"

json_escape_file() {
    if [ ! -f "$1" ]; then
        echo ""
        return
    fi

    cat "$1" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}'
}

send_webhook() {
    status=$1
    exit_code=$2

    logs=""
    if [ -f "$LOG_FILE" ]; then
        logs=$(json_escape_file "$LOG_FILE")
    fi

    stdout_value=$(json_escape_file "$STDOUT_FILE")
    stderr_value=$(json_escape_file "$STDERR_FILE")

    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    payload=$(cat <<EOF
{
  "uuid": "${UUID}",
  "status": "${status}",
  "exit_code": ${exit_code},
  "stdout": "${stdout_value}",
  "stderr": "${stderr_value}",
  "logs": "${logs}",
  "timestamp": "${timestamp}"
}
EOF
)

    echo "Sending webhook notification: status=${status}, exit_code=${exit_code}"

    for i in 1 2 3; do
        if curl -X POST "${WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            --max-time 30 \
            --silent \
            --show-error; then
            echo "Webhook sent successfully"
            return 0
        fi
        echo "Webhook attempt $i failed, retrying..."
        sleep 2
    done

    echo "Failed to send webhook after 3 attempts"
    return 1
}

trap 'send_webhook "failed" $?' EXIT INT TERM

echo "Starting Py Dispatcher Job"
echo "UUID: ${UUID}"
echo "Webhook: ${WEBHOOK_URL}"
echo "---"

if python -m src > "$LOG_FILE" 2>&1; then
    cat "$LOG_FILE"
    EXIT_CODE=0
    send_webhook "success" $EXIT_CODE
    trap - EXIT INT TERM
    exit $EXIT_CODE
else
    cat "$LOG_FILE"
    EXIT_CODE=$?
    send_webhook "failed" $EXIT_CODE
    trap - EXIT INT TERM
    exit $EXIT_CODE
fi


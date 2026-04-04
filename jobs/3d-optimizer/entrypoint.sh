#!/bin/sh
set -e

# Capture logs to a file
LOG_FILE="/tmp/job.log"

# Function to send webhook with logs
send_webhook() {
    local status=$1
    local exit_code=$2
    
    # Read logs
    local logs=""
    if [ -f "$LOG_FILE" ]; then
        logs=$(cat "$LOG_FILE")
    fi
    
    # Prepare JSON payload
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Escape logs for JSON (replace newlines and quotes)
    logs=$(echo "$logs" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}')

    local source_size=0
    local dest_size=0
    [ -f /tmp/source_size ] && source_size=$(cat /tmp/source_size)
    [ -f /tmp/optimized_size ] && dest_size=$(cat /tmp/optimized_size)

    local payload=$(cat <<EOF
{
  "uuid": "${UUID}",
  "status": "${status}",
  "exit_code": ${exit_code},
  "logs": "${logs}",
  "timestamp": "${timestamp}",
  "source_url": "${SOURCE_GLM_URL}",
  "dest_url": "${DEST_GLM_URL}",
  "source_file_size": ${source_size},
  "processed_file_size": ${dest_size}
}
EOF
)
    
    echo "Sending webhook notification: status=${status}, exit_code=${exit_code}"
    
    # Send webhook (retry up to 3 times)
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

# Trap all exit signals
trap 'send_webhook "failed" $?' EXIT INT TERM

echo "Starting 3D Optimizer Job"
echo "UUID: ${UUID}"
echo "Source: ${SOURCE_GLM_URL}"
echo "Destination: ${DEST_GLM_URL}"
echo "Webhook: ${WEBHOOK_URL}"
echo "---"

# Run the actual job and capture output
if ./3d-optimizer 2>&1 | tee "$LOG_FILE"; then
    # Job succeeded
    EXIT_CODE=0
    send_webhook "success" $EXIT_CODE
    trap - EXIT INT TERM
    exit $EXIT_CODE
else
    # Job failed
    EXIT_CODE=$?
    send_webhook "failed" $EXIT_CODE
    trap - EXIT INT TERM
    exit $EXIT_CODE
fi

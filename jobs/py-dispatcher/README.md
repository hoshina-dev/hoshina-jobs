# Py Dispatcher Job

Kubernetes job that executes a one-line Python snippet and posts stdout/stderr to a webhook.

## Quick Start

### Docker

```bash
docker build -t py-dispatcher:latest .

python3 - <<'PY'
import base64
code = 'print("hello from dispatcher")'
print(base64.b64encode(code.encode()).decode())
PY

docker run --rm \
  -e PY_CODE_B64="<paste-b64-output>" \
  -e UUID="job-123" \
  -e WEBHOOK_URL="https://api.example.com/webhook" \
  py-dispatcher:latest
```

### Argo Workflows

```bash
# Apply the WorkflowTemplate
kubectl apply -f argo.yaml

# Submit a workflow
argo submit --from workflowtemplate/py-dispatcher \
  -p python-code-b64="<paste-b64-output>" \
  -p uuid="job-123" \
  -p webhook-url="https://api.example.com/webhook"

# More complex one-line example (for loop + conditional)
python3 - <<'PY'
import base64
code = "total=0;\nfor i in range(5):\n    total+=i if i%2==0 else 0;\nprint(f\"total_even={total}\")"
print(base64.b64encode(code.encode()).decode())
PY

argo submit --from workflowtemplate/py-dispatcher \
  -p python-code-b64="<paste-b64-output>" \
  -p uuid="job-124" \
  -p webhook-url="https://api.example.com/webhook"

# More complex program (helper function + JSON + loop)
python3 - <<'PY'
import base64
code = "import json;\n" \
       "def summarize(nums):\n" \
       "    return {\"count\": len(nums), \"sum\": sum(nums), \"max\": max(nums)}\n" \
       "data = json.loads('{\\"nums\\": [3, 5, 8, 13]}');\n" \
       "result = summarize(data['nums']);\n" \
       "print(json.dumps(result, sort_keys=True))"
print(base64.b64encode(code.encode()).decode())
PY

argo submit --from workflowtemplate/py-dispatcher \
  -p python-code-b64="<paste-b64-output>" \
  -p uuid="job-125" \
  -p webhook-url="https://api.example.com/webhook"
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `PY_CODE_B64` | Base64-encoded Python code to execute |
| `UUID` | Unique job identifier |
| `WEBHOOK_URL` | Endpoint for completion notifications |

## Webhook Payload

```json
{
  "uuid": "job-123",
  "status": "success|failed",
  "exit_code": 0,
  "stdout": "Standard output...",
  "stderr": "Standard error...",
  "logs": "Complete job logs...",
  "timestamp": "2026-05-16T21:00:00Z"
}
```

Webhook is always attempted even on failure.

## Local Run

```bash
python3 - <<'PY'
import base64
code = 'print(2 + 2)'
print(base64.b64encode(code.encode()).decode())
PY

PY_CODE_B64="<paste-b64-output>" \
UUID="job-123" \
WEBHOOK_URL="https://api.example.com/webhook" \
python -m src

# More complex one-line example (for loop + list build)
python3 - <<'PY'
import base64
code = "items=[];\nfor i in range(3):\n    items.append(i*i);\nprint(\"squares=\", items)"
print(base64.b64encode(code.encode()).decode())
PY

PY_CODE_B64="<paste-b64-output>" \
UUID="job-124" \
WEBHOOK_URL="https://api.example.com/webhook" \
python -m src

# More complex program (helper function + JSON + loop)
python3 - <<'PY'
import base64
code = "import json;\n" \
       "def summarize(nums):\n" \
       "    return {\"count\": len(nums), \"sum\": sum(nums), \"max\": max(nums)}\n" \
       "data = json.loads('{\\"nums\\": [3, 5, 8, 13]}');\n" \
       "result = summarize(data['nums']);\n" \
       "print(json.dumps(result, sort_keys=True))"
print(base64.b64encode(code.encode()).decode())
PY

PY_CODE_B64="<paste-b64-output>" \
UUID="job-125" \
WEBHOOK_URL="https://api.example.com/webhook" \
python -m src
```

## Argo Workflow Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `python-code-b64` | Yes | - | Base64-encoded Python code |
| `uuid` | Yes | - | Unique job identifier |
| `webhook-url` | Yes | - | Webhook endpoint |

## Project Structure

```
py-dispatcher/
├── argo.yaml
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
├── src/
│   ├── __main__.py
│   └── main.py
└── README.md
```

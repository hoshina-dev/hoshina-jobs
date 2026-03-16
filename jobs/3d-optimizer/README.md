# 3D Optimizer Job

Kubernetes job that performs mesh reduction and DRACO compression on 3D GLB/GLTF models using pre-signed S3 URLs.

## Features

- ✅ Mesh reduction with gltf-pipeline
- ✅ DRACO compression with configurable quality
- ✅ Pre-signed S3 URLs (no AWS credentials needed)
- ✅ Guaranteed webhook notifications (success/failure/crash)
- ✅ Complete logs in webhook payload

## Quick Start

### Docker

```bash
docker build -t 3d-optimizer:latest .

docker run --rm \
  -e SOURCE_GLM_URL="https://s3.amazonaws.com/bucket/source.glb?X-Amz-..." \
  -e DEST_GLM_URL="https://s3.amazonaws.com/bucket/output.glb?X-Amz-..." \
  -e UUID="job-123" \
  -e WEBHOOK_URL="https://api.example.com/webhook" \
  3d-optimizer:latest
```

### Argo Workflows

```bash
# Apply the WorkflowTemplate
kubectl apply -f argo.yaml

# Submit a workflow
argo submit --from workflowtemplate/3d-optimizer \
  -p source-glm-url="https://s3.amazonaws.com/bucket/source.glb?X-Amz-..." \
  -p dest-glm-url="https://s3.amazonaws.com/bucket/output.glb?X-Amz-..." \
  -p uuid="job-123" \
  -p webhook-url="https://api.example.com/webhook"

# With custom optimization settings
argo submit --from workflowtemplate/3d-optimizer \
  -p source-glm-url="..." \
  -p dest-glm-url="..." \
  -p uuid="job-123" \
  -p webhook-url="https://api.example.com/webhook" \
  -p draco-compression-level="7" \
  -p draco-position-quantization="12"
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SOURCE_GLM_URL` | Pre-signed GET URL for source GLB/GLTF file |
| `DEST_GLM_URL` | Pre-signed PUT URL for optimized output file |
| `UUID` | Unique job identifier |
| `WEBHOOK_URL` | Endpoint for completion notifications |

### Optional (Optimization)

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `DRACO_COMPRESSION_LEVEL` | 10 | 0-10 | Compression level (higher = smaller) |
| `DRACO_POSITION_QUANTIZATION` | 14 | 8-30 | Vertex position precision |
| `DRACO_TEXCOORD_QUANTIZATION` | 12 | 8-30 | UV coordinate precision |
| `DRACO_NORMAL_QUANTIZATION` | 10 | 8-30 | Surface normal precision |
| `DRACO_GENERIC_QUANTIZATION` | 8 | 8-30 | Other attributes precision |

## How It Works

1. **Download** - HTTP GET from pre-signed `SOURCE_GLM_URL`
2. **Mesh Reduction** - gltf-pipeline with DRACO compression
3. **DRACO Encoding** - draco_encoder with configurable quality
4. **Upload** - HTTP PUT to pre-signed `DEST_GLM_URL`
5. **Webhook** - POST status, exit code, and complete logs

**No AWS SDK or credentials required** - uses simple HTTP operations.

## Webhook Payload

```json
{
  "uuid": "job-123",
  "status": "success|failed",
  "exit_code": 0,
  "logs": "Complete job logs including all output...",
  "timestamp": "2026-03-16T21:00:00Z"
}
```

Webhook is **always sent** even if pod crashes or is killed.

## Optimization Presets

### Maximum Compression (Default)
Best for web/mobile delivery
```bash
DRACO_COMPRESSION_LEVEL=10
DRACO_POSITION_QUANTIZATION=14
DRACO_TEXCOORD_QUANTIZATION=12
DRACO_NORMAL_QUANTIZATION=10
DRACO_GENERIC_QUANTIZATION=8
```
Result: Smallest files, ~30-60s processing

### Balanced Quality
Good quality with reasonable size
```bash
DRACO_COMPRESSION_LEVEL=7
DRACO_POSITION_QUANTIZATION=12
DRACO_TEXCOORD_QUANTIZATION=10
DRACO_NORMAL_QUANTIZATION=8
DRACO_GENERIC_QUANTIZATION=8
```
Result: 20-30% larger, ~15-30s processing

### Fast Encoding
Quick processing, larger files
```bash
DRACO_COMPRESSION_LEVEL=3
DRACO_POSITION_QUANTIZATION=11
DRACO_TEXCOORD_QUANTIZATION=10
DRACO_NORMAL_QUANTIZATION=8
DRACO_GENERIC_QUANTIZATION=8
```
Result: 40-50% larger, ~5-15s processing

## Pre-Signed URL Generation

Generate URLs in your dispatcher service:

```go
import (
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/service/s3"
    "time"
)

// Source: GET with 15min expiry
sourceReq, _ := s3Client.GetObjectRequest(&s3.GetObjectInput{
    Bucket: aws.String("my-bucket"),
    Key:    aws.String("models/source.glb"),
})
sourceURL, _ := sourceReq.Presign(15 * time.Minute)

// Destination: PUT with 15min expiry
destReq, _ := s3Client.PutObjectRequest(&s3.PutObjectInput{
    Bucket: aws.String("my-bucket"),
    Key:    aws.String("optimized/output.glb"),
})
destURL, _ := destReq.Presign(15 * time.Minute)
```

**Recommended expiry:** 15-30 minutes (typical job: 1-5 min, large models: 10-15 min)

## Example Logs

### Success
```
Starting 3D Optimizer Job
UUID: job-123
Source: https://s3.amazonaws.com/bucket/source.glb?X-Amz-...
---
2026/03/16 21:30:00 Starting job execution
2026/03/16 21:30:00 Downloading source file from: https://s3...
2026/03/16 21:30:05 Source file downloaded successfully (15728640 bytes)
2026/03/16 21:30:05 Processing 3D optimization
2026/03/16 21:30:05 Starting mesh reduction (compression level: 10)...
2026/03/16 21:30:25 Mesh reduction completed (output: 12582912 bytes)
2026/03/16 21:30:25 Starting DRACO compression (CL:10, QP:14, QT:12, QN:10, QG:8)...
2026/03/16 21:30:45 DRACO compression completed (output: 3145728 bytes)
2026/03/16 21:30:45 Uploading result file to: https://s3...
2026/03/16 21:30:50 Result file uploaded successfully (3145728 bytes)
2026/03/16 21:30:50 Job completed successfully
Sending webhook notification: status=success, exit_code=0
Webhook sent successfully
```

**Compression:** 15.7 MB → 3.1 MB (80% reduction)

### Failure
```
2026/03/16 21:31:00 Downloading source file from: https://s3...
2026/03/16 21:31:05 Job failed: download source file: unexpected status code: 404
Sending webhook notification: status=failed, exit_code=1
Webhook sent successfully
```

## Argo Workflow Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `source-glm-url` | Yes | - | Pre-signed GET URL for source file |
| `dest-glm-url` | Yes | - | Pre-signed PUT URL for output file |
| `uuid` | Yes | - | Unique job identifier |
| `webhook-url` | Yes | - | Webhook endpoint |
| `draco-compression-level` | No | 10 | Compression level (0-10) |
| `draco-position-quantization` | No | 14 | Position quantization (8-30) |
| `draco-texcoord-quantization` | No | 12 | TexCoord quantization (8-30) |
| `draco-normal-quantization` | No | 10 | Normal quantization (8-30) |
| `draco-generic-quantization` | No | 8 | Generic quantization (8-30) |

## Project Structure

```
3d-optimizer/
├── cmd/main.go          # Entry point
├── internal/
│   ├── config.go       # Environment config
│   └── job.go          # Optimization logic
├── entrypoint.sh       # Webhook wrapper
├── Dockerfile          # Multi-stage build
├── argo.yaml           # Argo WorkflowTemplate
└── README.md
```

## Security

- ✅ No AWS credentials in container
- ✅ No IAM roles needed
- ✅ Time-limited access via URL expiration
- ✅ Scoped permissions (read source, write destination only)
- ✅ Each job gets unique URLs

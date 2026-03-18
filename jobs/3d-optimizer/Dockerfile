# Build stage
FROM golang:1.25.0-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o 3d-optimizer cmd/main.go

# Final stage
FROM node:20-alpine

# Install system dependencies
RUN apk --no-cache add \
    ca-certificates \
    curl \
    bash

# Install gltf-pipeline (includes DRACO compression)
RUN npm install -g gltf-pipeline

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/3d-optimizer .

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Use entrypoint script that handles webhook notifications
ENTRYPOINT ["./entrypoint.sh"]

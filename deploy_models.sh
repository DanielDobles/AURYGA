#!/bin/bash
set -e

echo "=== Arcaios Forge — vLLM Multi-Model Deployment on MI300X ==="
echo "=== Cleaning up existing containers... ==="
docker rm -f vllm-coder vllm-reasoning vllm-audio 2>/dev/null || true
sleep 3

echo "=== Step 1: Qwen2.5-Coder-32B (port 8000) — Code generation ==="
docker run -d \
    --name vllm-coder \
    --restart unless-stopped \
    --network=host \
    --group-add=video \
    --ipc=host \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --device /dev/kfd \
    --device /dev/dri \
    -v /root/.cache/huggingface:/root/.cache/huggingface \
    rocm/vllm:latest \
    vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
        --host 0.0.0.0 \
        --port 8000 \
        --gpu-memory-utilization 0.42 \
        --max-model-len 8192 \
        --dtype float16 \
        --enable-auto-tool-choice \
        --tool-call-parser hermes \
        --trust-remote-code

echo "--- Waiting for Coder model to fully load before launching Reasoning... ---"
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
        echo "--- Coder is READY on port 8000 ---"
        break
    fi
    echo "  waiting... ($i/60)"
    sleep 5
done

echo "=== Step 2: Qwen3-32B (port 8001) — Reasoning agent ==="
docker run -d \
    --name vllm-reasoning \
    --restart unless-stopped \
    --network=host \
    --group-add=video \
    --ipc=host \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --device /dev/kfd \
    --device /dev/dri \
    -v /root/.cache/huggingface:/root/.cache/huggingface \
    rocm/vllm:latest \
    vllm serve Qwen/Qwen3-32B \
        --host 0.0.0.0 \
        --port 8001 \
        --gpu-memory-utilization 0.42 \
        --max-model-len 8192 \
        --dtype float16 \
        --enable-auto-tool-choice \
        --tool-call-parser hermes \
        --trust-remote-code

echo "=== DEPLOY COMPLETE ==="

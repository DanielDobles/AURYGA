#!/bin/bash
set -e

echo "=== Arcaios Forge — vLLM Multi-Model Deployment on MI300X ==="
echo "=== GPU: AMD Instinct MI300X (192GB HBM3) ==="
echo "=== Stack: ROCm 7.2 / Ubuntu 24.04 ==="
echo ""

echo "=== Step 1: Pull vLLM ROCm Docker image ==="
docker pull rocm/vllm:latest

echo "=== Step 2: Qwen2.5-Coder-32B (port 8000) — Code generation agents ==="
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
        --gpu-memory-utilization 0.35 \
        --max-model-len 16384 \
        --dtype float16 \
        --trust-remote-code

echo "=== Step 3: Qwen3-32B (port 8001) — Reasoning agent ==="
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
        --gpu-memory-utilization 0.35 \
        --max-model-len 16384 \
        --dtype float16 \
        --trust-remote-code

echo "=== Step 4: Qwen2-Audio-7B (port 8002) — Audio analysis agent ==="
docker run -d \
    --name vllm-audio \
    --restart unless-stopped \
    --network=host \
    --group-add=video \
    --ipc=host \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --device /dev/kfd \
    --device /dev/dri \
    -v /root/.cache/huggingface:/root/.cache/huggingface \
    -v /root/arcaios_run:/audio \
    rocm/vllm:latest \
    vllm serve Qwen/Qwen2-Audio-7B-Instruct \
        --host 0.0.0.0 \
        --port 8002 \
        --gpu-memory-utilization 0.20 \
        --max-model-len 8192 \
        --dtype float16 \
        --trust-remote-code

echo ""
echo "=== Containers launched ==="
echo "Coder API (Qwen2.5-Coder-32B):  http://0.0.0.0:8000/v1"
echo "Reasoning API (Qwen3-32B):       http://0.0.0.0:8001/v1"
echo "Audio API (Qwen2-Audio-7B):      http://0.0.0.0:8002/v1"
echo ""
echo "Models will download from HuggingFace on first launch (~60GB total)."
echo "Monitor with:"
echo "  docker logs -f vllm-coder"
echo "  docker logs -f vllm-reasoning"
echo "  docker logs -f vllm-audio"
echo "=== DEPLOY COMPLETE ==="

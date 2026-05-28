#!/bin/bash

# Exit immediately if any command exits with a non-zero status
set -e

echo "========================================================"
echo "🚀 STARTING E-COMMERCE CONTENT STUDIO AI FOR PRODUCTION"
echo "========================================================"

# Railway injects a dynamic port to the $PORT env variable.
# Streamlit must run on this public port.
TARGET_PORT=${PORT:-8501}
echo "[*] Streamlit will run on public Port: $TARGET_PORT"

# 1. Start FastAPI Backend (Uvicorn) in the background
echo "[*] Booting FastAPI backend on port 8800..."
uvicorn app.main:app --host 0.0.0.0 --port 8800 &

# Give Uvicorn 2 seconds to bind and initialize before starting Streamlit
sleep 2

# 2. Start Streamlit Dashboard in the foreground
echo "[*] Booting Streamlit dashboard on port $TARGET_PORT..."
streamlit run streamlit_app.py \
    --server.port "$TARGET_PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false

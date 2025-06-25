#!/bin/bash
set -e

echo "🚀 Starting RepairLift Dashboard deployment..."

# Check Python version
echo "🐍 Python version:"
python3 --version || python --version

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install --upgrade pip || python -m pip install --upgrade pip
python3 -m pip install -r requirements.txt || python -m pip install -r requirements.txt

# Start the server
echo "🌐 Starting server..."
python3 start_server.py || python start_server.py

#!/bin/bash

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Navigate to project directory (assuming script is run from project root)
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Install requirements
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "Setup complete. To run the bot, use: export PYTHONPATH=\$(pwd); ./venv/bin/python src/live_main.py"

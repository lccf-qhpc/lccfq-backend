#!/bin/bash
set -e

echo "🔧 Installing systemd services..."

# Watchdog
sudo cp ./scripts/lccfq-qpu-watchdog.service /etc/systemd/system/
sudo systemctl enable lccfq-qpu-watchdog.service

# Backend
sudo cp ./scripts/lccfq-backend.service /etc/systemd/system/
sudo systemctl enable lccfq-backend.service

# Reload and start
sudo systemctl daemon-reload
sudo systemctl start lccfq-qpu-watchdog.service
sudo systemctl start lccfq-backend.service

echo "✅ All services installed and started successfully."
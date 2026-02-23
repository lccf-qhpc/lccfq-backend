#!/bin/bash
set -e
SERVICE_PATH="/etc/systemd/system/lccfq-qpu-watchdog.service"

sudo cp ./scripts/lccfq-qpu-watchdog.service $SERVICE_PATH
sudo systemctl daemon-reload
sudo systemctl enable lccfq-qpu-watchdog.service
sudo systemctl start lccfq-qpu-watchdog.service
echo "✅ QPU Watchdog installed and started successfully."
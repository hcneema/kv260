#!/bin/bash
# Usage: ~/tunnel.sh <HOST_USER> <HOST_FQDN> [TUNNEL_PORT]
# Starts a reverse SSH tunnel from this board to the user's VDI host.
# Works whether or not Wi-Fi is connected on the board.
set -e

HOST_USER="${1:?Usage: ~/tunnel.sh <HOST_USER> <HOST_FQDN> [TUNNEL_PORT]}"
HOST_FQDN="${2:?Usage: ~/tunnel.sh <HOST_USER> <HOST_FQDN> [TUNNEL_PORT]}"
TUNNEL_PORT="${3:-2222}"

# --- Wi-Fi coexistence fix ---
# If Wi-Fi is active, prevent it from becoming the default route.
# This is idempotent and harmless if Wi-Fi is not connected.
for conn in $(nmcli -t -f NAME,TYPE connection show --active 2>/dev/null \
              | grep ':802-11-wireless$' | cut -d: -f1); do
  sudo nmcli connection modify "$conn" ipv4.never-default yes ipv6.never-default yes 2>/dev/null || true
  sudo nmcli connection up "$conn" 2>/dev/null || true
done

# Kill any existing reverse tunnel
pkill -f "ssh.*-R ${TUNNEL_PORT}:localhost:22" 2>/dev/null || true
sleep 1

# Start the reverse tunnel in the background
nohup ssh \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=accept-new \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -N -R "${TUNNEL_PORT}:localhost:22" \
  "${HOST_USER}@${HOST_FQDN}" \
  > /dev/null 2>&1 &

echo "Reverse tunnel started: localhost:22 -> ${HOST_FQDN}:${TUNNEL_PORT}"

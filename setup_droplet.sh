#!/bin/bash
set -e

echo "=== Stopping unattended-upgrades ==="
systemctl stop unattended-upgrades 2>/dev/null || true
systemctl disable unattended-upgrades 2>/dev/null || true
killall unattended-upgr 2>/dev/null || true
sleep 3

echo "=== Waiting for any dpkg lock ==="
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    echo "Still locked, waiting..."
    sleep 5
done

echo "=== Configuring dpkg ==="
dpkg --configure -a 2>/dev/null || true

echo "=== Updating apt ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

echo "=== Installing Faust ==="
apt-get install -y -qq faust

echo "=== Installing SuperCollider ==="
apt-get install -y -qq supercollider-server supercollider-language supercollider-dev

echo "=== Installing xvfb, zip, sox ==="
apt-get install -y -qq xvfb zip unzip sox libsndfile1

echo "=== Verification ==="
echo "faust: $(which faust 2>/dev/null || echo NOT_FOUND)"
echo "sclang: $(which sclang 2>/dev/null || echo NOT_FOUND)"
echo "xvfb-run: $(which xvfb-run 2>/dev/null || echo NOT_FOUND)"
echo "zip: $(which zip 2>/dev/null || echo NOT_FOUND)"
echo "sox: $(which sox 2>/dev/null || echo NOT_FOUND)"
faust --version 2>/dev/null || echo "faust version check failed"
echo "=== SETUP COMPLETE ==="

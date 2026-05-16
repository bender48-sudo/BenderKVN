#!/bin/bash
# Read-only probe invoked over SSH by the NL watchdog. Returns log mtimes.
echo "monitor_sh=$(stat -c %Y /var/log/bvpn-monitor.log 2>/dev/null || echo 0)"
echo "ru_monitor=$(stat -c %Y /var/log/bvpn-ru-monitor.log 2>/dev/null || echo 0)"
echo "now=$(date +%s)"

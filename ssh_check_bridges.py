#!/usr/bin/env python3
import subprocess
import sys
import os

os.environ['SSHPASS'] = '1234'

# Use sshpass + ssh for better reliability
cmd = [
    'ssh',
    '-o', 'ConnectTimeout=30',
    '-o', 'StrictHostKeyChecking=no',
    'fathertkt@100.125.63.77',
    'cd /home/fathertkt/prism-backend && docker compose ps | grep -E "CONTAINER|prism-whatsapp|prism-meta|prism-synapse"'
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except subprocess.TimeoutExpired:
    print("SSH command timed out")
except Exception as e:
    print(f"Error: {e}")

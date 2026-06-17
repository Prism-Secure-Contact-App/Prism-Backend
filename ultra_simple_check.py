#!/usr/bin/env python3
import socket
import time

# First check if server is reachable via ping/socket
try:
    socket.create_connection(("100.125.63.77", 22), timeout=5)
    print("✅ Server is reachable on SSH port\n")
except:
    print("❌ Server not reachable on SSH port\n")
    exit(1)

# Try SSH one more time with very short timeout
import paramiko

try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30, auth_timeout=10)
    
    # VERY SIMPLE command - just get container names and status
    stdin, stdout, stderr = c.exec_command("docker ps --no-trunc --format '{{.Names}},{{.Status}}'", timeout=10)
    result = stdout.read(1024).decode('utf-8', errors='ignore')
    
    print("CONTAINER STATUS:\n")
    for line in result.split("\n"):
        if line.strip() and "prism-" in line:
            parts = line.split(",")
            name = parts[0] if parts else "?"
            status = parts[1] if len(parts) > 1 else "?"
            
            # Simple check
            if "Up" in status:
                icon = "✅"
            elif "Restarting" in status:
                icon = "🔄"
            else:
                icon = "⚠️"
            
            print(f"{icon} {name}: {status[:40]}")
    
    c.close()
    
except Exception as e:
    print(f"SSH Error: {str(e)[:100]}")

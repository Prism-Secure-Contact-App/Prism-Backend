#!/usr/bin/env python3
"""
Final bridge status check - after downgrading to legacy-config-supporting versions
"""
import paramiko
import sys
import time

try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)
    
    # Get status
    stdin, stdout, stderr = c.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'", timeout=10)
    status_output = stdout.read(2048).decode('utf-8', errors='ignore')
    
    print("\n" + "="*70)
    print("BRIDGE STATUS - AFTER VERSION DOWNGRADE")
    print("="*70 + "\n")
    
    wa_up = meta_up = synapse_ok = False
    
    for line in status_output.split("\n"):
        if "prism-whatsapp" in line:
            is_up = "Up" in line and "Restarting" not in line
            wa_up = is_up
            icon = "✅" if is_up else "⚠️"
            print(f"{icon} WhatsApp: {line.strip()[30:]}")
        elif "prism-meta" in line:
            is_up = "Up" in line and "Restarting" not in line
            meta_up = is_up
            icon = "✅" if is_up else "⚠️"
            print(f"{icon} Meta: {line.strip()[30:]}")
        elif "prism-synapse" in line:
            synapse_ok = "Up" in line
            icon = "✅" if synapse_ok else "⚠️"
            print(f"{icon} Synapse: {line.strip()[30:]}")
    
    print("\n" + "="*70)
    
    if wa_up and meta_up and synapse_ok:
        print("🎉 SUCCESS! BRIDGES ARE RUNNING!")
        print("="*70)
        sys.exit(0)
    else:
        print("⚠️ Bridges are still not running properly")
        print("="*70)
        
        # Get brief error info
        if not wa_up:
            stdin, stdout, stderr = c.exec_command("docker logs prism-whatsapp 2>&1 | tail -3", timeout=5)
            log_line = stdout.read(500).decode('utf-8', errors='ignore').strip()
            if log_line:
                print(f"\nWhatsApp last log: {log_line[:80]}")
        
        sys.exit(1)
    
    c.close()
    
except Exception as e:
    print(f"\n❌ Error: {str(e)[:100]}")
    sys.exit(1)

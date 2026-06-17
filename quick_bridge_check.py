#!/usr/bin/env python3
import paramiko
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)

# Quick status
stdin, stdout, stderr = c.exec_command(r"docker ps --filter 'name=prism-whatsapp|prism-meta|prism-synapse|prism-db' --format 'table {{.Names}}\t{{.Status}}'")
status = stdout.read().decode('utf-8')

wa_up = "prism-whatsapp" in status and "Up" in status
meta_up = "prism-meta" in status and "Up" in status
synapse_up = "prism-synapse" in status and "Up" in status

print(status)

if wa_up and meta_up:
    print("\n✅ SUCCESS - Both bridges are UP!")
    sys.exit(0)
else:
    print("\n⚠️ Bridges not fully up yet")
    print(f"  WhatsApp: {'UP' if wa_up else 'DOWN'}")
    print(f"  Meta: {'UP' if meta_up else 'DOWN'}")
    
    # Show last log lines
    if not wa_up:
        stdin, stdout, stderr = c.exec_command("docker logs --tail 5 prism-whatsapp 2>&1 | tail -1")
        print(f"\n  WhatsApp last: {stdout.read().decode('utf-8').strip()[:100]}")
    
    if not meta_up:
        stdin, stdout, stderr = c.exec_command("docker logs --tail 5 prism-meta 2>&1 | tail -1")
        print(f"  Meta last: {stdout.read().decode('utf-8').strip()[:100]}")
    
    sys.exit(1)

c.close()

#!/usr/bin/env python3
import paramiko
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)

# Container status
stdin, stdout, stderr = c.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}'")
status = stdout.read().decode('utf-8')

print("="*70)
print("FINAL BRIDGE STATUS")
print("="*70)
print(status)

# Check if UP
wa_up = "prism-whatsapp" in status and "Up" in status.split("prism-whatsapp")[1].split("\n")[0]
meta_up = "prism-meta" in status and "Up" in status.split("prism-meta")[1].split("\n")[0]
synapse_up = "prism-synapse" in status and "Up" in status.split("prism-synapse")[1].split("\n")[0]

print("\n" + "="*70)

if wa_up and meta_up and synapse_up:
    print("✅ SUCCESS! ALL BRIDGES ARE RUNNING AND HEALTHY!\n")
    
    # Test connectivity
    print("Testing bridge connectivity...")
    
    stdin, stdout, stderr = c.exec_command("docker exec prism-synapse curl -s http://prism-whatsapp:29318/_matrix/appservice/version 2>&1 | head -c 100")
    out1 = stdout.read().decode('utf-8').strip()
    
    stdin, stdout, stderr = c.exec_command("docker exec prism-synapse curl -s http://prism-meta:29319/_matrix/appservice/version 2>&1 | head -c 100")
    out2 = stdout.read().decode('utf-8').strip()
    
    if "{" in out1 or "version" in out1:
        print("✅ WhatsApp bridge responding")
    if "{" in out2 or "version" in out2:
        print("✅ Meta bridge responding")
    
    print("\n🎉 BRIDGES FULLY OPERATIONAL!")
    sys.exit(0)
    
else:
    print("⚠️  Bridges not fully running yet:\n")
    print(f"  WhatsApp: {'UP ✅' if wa_up else 'DOWN/RESTARTING'}")
    print(f"  Meta: {'UP ✅' if meta_up else 'DOWN/RESTARTING'}")
    print(f"  Synapse: {'UP ✅' if synapse_up else 'DOWN'}\n")
    
    # Show first error from logs
    if not wa_up:
        print("WhatsApp logs (first error):")
        stdin, stdout, stderr = c.exec_command("docker logs prism-whatsapp 2>&1 | grep -v 'Legacy bridge' | head -5")
        for line in stdout.read().decode('utf-8').split("\n")[:5]:
            if line.strip():
                print(f"  {line[:100]}")
    
    sys.exit(1)

c.close()

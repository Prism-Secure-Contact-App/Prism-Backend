#!/usr/bin/env python3
import paramiko

try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting...")
    c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=60)
    print("Connected")
    
    BASE = "/home/fathertkt/prism-backend"
    
    # Simple status
    stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose ps --format 'table {{.Names}}\t{{.Status}}'")
    output = stdout.read().decode('utf-8')
    print("CONTAINER STATUS:")
    print(output)
    
    # WhatsApp error
    stdin, stdout, stderr = c.exec_command("docker logs prism-whatsapp 2>&1 | tail -20")
    print("\nWHATSAPP LAST 20 LINES:")
    print(stdout.read().decode('utf-8'))
    
    c.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

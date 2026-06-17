#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

print("🎯 FİNAL DURUM:\n")

# Synapse appservice log
stdin, stdout, stderr = c.exec_command("docker logs --tail 20 prism-synapse 2>&1 | grep -i 'appservice\\|permission\\|reuse\\|loaded'")
out = stdout.read().decode('utf-8')

if "permission" in out.lower() or "reuse" in out.lower() or "error" in out.lower():
    print("❌ HATALAR VAR:")
    for line in out.split("\n"):
        if line.strip():
            print(f"  {line[:100]}")
else:
    print("✅ SYNAPSE APPSERVICE HATASI YOK!")

# Bridge port'ları
print("\n🔌 Bridge Port'ları:")

for svc in ["whatsapp", "meta"]:
    stdin, stdout, stderr = c.exec_command(f"docker exec prism-{svc} netstat -tulpn 2>/dev/null | grep LISTEN")
    out = stdout.read().decode('utf-8').strip()
    if "LISTEN" in out:
        print(f"  ✅ {svc} listening")
    else:
        print(f"  ⚠️  {svc} not listening yet (restarting)")

# Appservice URL test
print("\n🌐 AppService Accessibility Test:")

for svc, port in [("whatsapp", "29318"), ("meta", "29319")]:
    stdin, stdout, stderr = c.exec_command(f"docker exec prism-synapse curl -s http://prism-{svc}:{port} 2>&1 | head -c 100")
    out = stdout.read().decode('utf-8').strip()
    if out and "html" not in out.lower() and "connection refused" not in out.lower():
        print(f"  ✅ {svc}:{port} erişilebilir")
    elif "connection refused" in out.lower():
        print(f"  ⚠️  {svc}:{port} henüz hazır değil")
    else:
        print(f"  {svc}:{port}: {out[:50]}")

c.close()

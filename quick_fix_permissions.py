import paramiko
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

BASE = "/home/fathertkt/prism-backend"

print("🔍 Docker container user'larını kontrol ediyor...")

# Hangi user ile çalıştığını kontrol et
for svc in ["whatsapp", "meta"]:
    cmd = f"docker inspect prism-{svc} --format='{{{{.Config.User}}}}'"
    stdin, stdout, stderr = c.exec_command(cmd)
    user = stdout.read().decode('utf-8').strip()
    print(f"  prism-{svc}: user={user if user else 'root'}")

print("\n🔍 Config dosyaları kontrol ediliyor...")
for f in ["whatsapp", "meta"]:
    cmd = f"ls -la {BASE}/data/{f}/config.yaml"
    stdin, stdout, stderr = c.exec_command(cmd)
    print(f"  {stdout.read().decode('utf-8').strip()}")

print("\n✏️  Dosya permission'larını 666 olarak ayarlıyor...")
stdin, stdout, stderr = c.exec_command(f"sudo chmod 666 {BASE}/data/whatsapp/config.yaml {BASE}/data/whatsapp/registration.yaml {BASE}/data/meta/config.yaml {BASE}/data/meta/registration.yaml 2>&1")
out = stdout.read().decode('utf-8')
if out.strip():
    print(out)

print("\n✏️  Klasör permission'larını 777 olarak ayarlıyor...")
stdin, stdout, stderr = c.exec_command(f"sudo chmod 777 {BASE}/data/whatsapp {BASE}/data/meta 2>&1")

print("\n🔍 Güncellenmiş permission'lar:")
for f in ["whatsapp", "meta"]:
    cmd = f"ls -la {BASE}/data/{f}/config.yaml"
    stdin, stdout, stderr = c.exec_command(cmd)
    print(f"  {stdout.read().decode('utf-8').strip()}")

print("\n🔄 Bridge servisleri stop ediliyor...")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose stop whatsapp meta")
time.sleep(3)

print("🔄 Bridge servisleri start ediliyor...")
stdin, stdout, stderr = c.exec_command(f"cd {BASE} && docker compose up -d whatsapp meta")
time.sleep(15)

print("\n✅ Container Status:")
stdin, stdout, stderr = c.exec_command("docker ps --filter 'name=prism' --format 'table {{.Names}}\t{{.Status}}'")
print(stdout.read().decode('utf-8'))

print("\n📍 Bridge Logs:")
for svc in ["whatsapp", "meta"]:
    print(f"\n{svc.upper()}:")
    stdin, stdout, stderr = c.exec_command(f"docker logs --tail 5 prism-{svc} 2>&1")
    lines = stdout.read().decode('utf-8').split("\n")
    for line in lines[-5:]:
        if line.strip():
            print(f"  {line[:100]}")

c.close()

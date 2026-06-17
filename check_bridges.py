#!/usr/bin/env python3
"""
Bridge Health Check & Debug Script

WhatsApp ve Meta bridge'lerin sağlık durumunu kontrol et:
- Container status
- AppService registration
- Message routing
- Error logs
"""

import paramiko
import os
import sys
from pathlib import Path


def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"❌ HATA: '{key}' ortam değişkeni eksik.")
        sys.exit(1)
    return val


PI_HOST = _require_env("PI_HOST")
PI_USER = _require_env("PI_USER")
PI_PASS = _require_env("PI_PASS")
SERVER_NAME = _require_env("SERVER_NAME")


def ssh_connect(host, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)
    return client


def run_cmd(client, cmd, print_output=True):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if print_output and out.strip():
        print(out.strip())
    return out, err


def check_container_status(client):
    """Container'ların ayakta olup olmadığını kontrol et"""
    print("\n" + "=" * 60)
    print("🐳 CONTAINER STATUS")
    print("=" * 60)
    
    out, _ = run_cmd(client, "docker ps --format 'table {{.Names}}\t{{.Status}}'", print_output=False)
    
    containers = ["prism-synapse", "prism-whatsapp", "prism-meta"]
    for cont in containers:
        if cont in out:
            status = [line for line in out.split("\n") if cont in line]
            if status:
                print(f"✅ {status[0]}")
        else:
            print(f"❌ {cont} çalışmıyor!")
    
    return True


def check_appservice_registration(client, matrix_dir="/opt/matrix-server"):
    """AppService registration dosyalarını kontrol et"""
    print("\n" + "=" * 60)
    print("📋 APPSERVICE REGISTRATION")
    print("=" * 60)
    
    for service in ["whatsapp", "meta"]:
        yaml_file = f"{matrix_dir}/data/synapse/appservice-{service}.yaml"
        print(f"\n📄 {service} registration:")
        
        out, _ = run_cmd(client, f"[ -f {yaml_file} ] && echo 'EXISTS' || echo 'MISSING'", print_output=False)
        
        if "EXISTS" not in out:
            print(f"  ❌ Dosya bulunamadı: {yaml_file}")
            continue
        
        # Read key fields
        fields = ["id:", "url:", "sender_localpart:", "rate_limited:", "encryption:"]
        for field in fields:
            out, _ = run_cmd(client, f"grep '{field}' {yaml_file} | head -1", print_output=False)
            if out.strip():
                print(f"  {out.strip()}")
    
    return True


def check_homeserver_config(client, matrix_dir="/opt/matrix-server"):
    """homeserver.yaml'da appservice'lerin kayıtlı olup olmadığını kontrol et"""
    print("\n" + "=" * 60)
    print("🏠 HOMESERVER CONFIGURATION")
    print("=" * 60)
    
    homeserver_yaml = f"{matrix_dir}/data/synapse/homeserver.yaml"
    out, _ = run_cmd(client, f"grep -A10 'app_service_config_files:' {homeserver_yaml}", print_output=False)
    
    print("app_service_config_files:")
    print(out.strip() if out.strip() else "  (boş!)")
    
    if "appservice-whatsapp.yaml" not in out:
        print("  ⚠️  WhatsApp appservice missing!")
    if "appservice-meta.yaml" not in out:
        print("  ⚠️  Meta appservice missing!")
    
    return True


def check_bridge_connectivity(client):
    """Bridge'lerin Synapse ile bağlantısını kontrol et"""
    print("\n" + "=" * 60)
    print("🔗 BRIDGE CONNECTIVITY")
    print("=" * 60)
    
    for service, port in [("whatsapp", "29318"), ("meta", "29319")]:
        print(f"\n🔍 {service} bridge (port {port}):")
        
        # Check if bridge container is listening
        out, _ = run_cmd(
            client,
            f"docker exec prism-{service} netstat -tulpn 2>/dev/null | grep {port} || echo 'NOT_LISTENING'",
            print_output=False
        )
        
        if "LISTEN" in out:
            print(f"  ✅ Listening on port {port}")
        else:
            print(f"  ❌ Not listening on port {port}")
        
        # Check bridge logs for errors
        out, _ = run_cmd(
            client,
            f"docker logs --tail 30 prism-{service} 2>&1 | grep -i 'error\\|critical' | head -3",
            print_output=False
        )
        
        if out.strip():
            print(f"  ⚠️  Recent errors:")
            for line in out.split("\n")[:3]:
                if line.strip():
                    print(f"     {line.strip()[:80]}")
        else:
            print(f"  ✅ No recent errors")
    
    return True


def check_appservice_events(client):
    """Synapse log'larında appservice event'lerini kontrol et"""
    print("\n" + "=" * 60)
    print("📡 APPSERVICE EVENTS (Synapse Logs)")
    print("=" * 60)
    
    out, _ = run_cmd(
        client,
        "docker logs --tail 100 prism-synapse 2>&1 | grep -i 'POST /_matrix/app' | tail -5",
        print_output=False
    )
    
    if out.strip():
        print("Recent appservice calls:")
        for line in out.split("\n"):
            if line.strip():
                print(f"  {line.strip()[:100]}")
    else:
        print("No appservice events found in recent logs.")
        print("⚠️  This might mean:")
        print("  1. Appservice registration is not loaded")
        print("  2. No messages are being routed to bridges")
        print("  3. Bridges are not sending/receiving messages")
    
    return True


def check_bot_users(client, server_name):
    """Bot user'ları DB'de kontrol et"""
    print("\n" + "=" * 60)
    print("👤 BOT USERS")
    print("=" * 60)
    
    for bot, name in [("pwb-bot", "WhatsApp"), ("pmb-bot", "Meta")]:
        out, _ = run_cmd(
            client,
            f"docker exec prism-db psql -U synapse synapse -tc \"SELECT name, avatar_url, displayname FROM users WHERE name = '@{bot}:{server_name}' LIMIT 1;\" 2>&1",
            print_output=False
        )
        
        if bot in out or "|" in out:
            print(f"✅ {name} bot ({bot}):")
            print(f"   {out.strip()}")
        else:
            print(f"❌ {name} bot ({bot}) not found in database!")
    
    return True


def suggest_fixes(client):
    """Sorunlara çözüm öner"""
    print("\n" + "=" * 60)
    print("🔧 RECOMMENDED FIXES")
    print("=" * 60)
    
    print("""
If you see errors above, try these fixes in order:

1. **AppService files not found:**
   cd Backend
   python3 configure_whatsapp.py
   python3 configure_meta.py

2. **Containers not running:**
   docker compose up -d whatsapp meta synapse

3. **AppService not in homeserver.yaml:**
   cd Backend/data/synapse
   # Add to homeserver.yaml under app_service_config_files:
   #   - /data/appservice-whatsapp.yaml
   #   - /data/appservice-meta.yaml
   docker compose restart synapse

4. **Bot users not found:**
   # Create them via admin API or SQL:
   docker exec prism-db psql -U synapse synapse \\
     -c "INSERT INTO users (name, password_hash, creation_ts) \\
       VALUES ('@pwb-bot:matrix.fathertkt.uk', 'hashed_pwd', extract(epoch from now()));"

5. **Still not working:**
   cd Backend && python3 setup_bridges.py
    """)
    
    return True


def main():
    print("\n" + "=" * 60)
    print("🔍 PRISM BRIDGE HEALTH CHECK")
    print("=" * 60)
    
    try:
        client = ssh_connect(PI_HOST, PI_USER, PI_PASS)
        
        check_container_status(client)
        check_appservice_registration(client)
        check_homeserver_config(client)
        check_bridge_connectivity(client)
        check_appservice_events(client)
        check_bot_users(client, SERVER_NAME)
        suggest_fixes(client)
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

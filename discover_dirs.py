#!/usr/bin/env python3
"""Sunucu üzerinde matrix dizinini keşfet"""
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=30)

# Sunucu üzerindeki matrix dizinini bul
stdin, stdout, stderr = c.exec_command('find /home -name "homeserver.yaml" 2>/dev/null')
result = stdout.read().decode('utf-8').strip()
print(f"homeserver.yaml yolu: {result}")

# Docker compose dizini bul
stdin, stdout, stderr = c.exec_command('find /home -name "docker-compose.yml" 2>/dev/null | head -1')
result = stdout.read().decode('utf-8').strip()
print(f"docker-compose.yml yolu: {result}")

# Synapse container'ı kontrol et
stdin, stdout, stderr = c.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}"')
result = stdout.read().decode('utf-8')
print("\nContainer'lar:")
print(result)

# Synapse volume'ü kontrol et
stdin, stdout, stderr = c.exec_command('docker inspect prism-synapse | grep -A5 Mounts')
result = stdout.read().decode('utf-8')
print("\nSynapse volume mounts:")
print(result[:500])

c.close()

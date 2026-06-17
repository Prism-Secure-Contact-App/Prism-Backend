#!/usr/bin/env python3
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('100.125.63.77', username='fathertkt', password='1234', timeout=120, banner_timeout=120)

stdin, stdout, stderr = c.exec_command('cat /home/fathertkt/prism-backend/data/whatsapp/config.yaml', timeout=120)
content = stdout.read(timeout=120).decode('utf-8')

with open("whatsapp.yaml", "w") as f:
    f.write(content)

print("Downloaded whatsapp config")

stdin, stdout, stderr = c.exec_command('cat /home/fathertkt/prism-backend/data/meta/config.yaml', timeout=120)
content = stdout.read(timeout=120).decode('utf-8')

with open("meta.yaml", "w") as f:
    f.write(content)

print("Downloaded meta config")

c.close()

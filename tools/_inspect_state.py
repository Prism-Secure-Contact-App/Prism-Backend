"""Get the actual error message that's keeping bridges in CrashLoop."""
import paramiko, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "100.125.63.77"
USER = "fathertkt"
PASS = "1234"

CMDS = [
    "echo === whatsapp last 30 log lines (full) ===",
    f"echo {PASS} | sudo -S docker logs --tail 30 prism-whatsapp 2>&1",
    "echo",
    "echo === meta last 30 log lines (full) ===",
    f"echo {PASS} | sudo -S docker logs --tail 30 prism-meta 2>&1",
]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=10)
for cmd in CMDS:
    _, out, err = c.exec_command(cmd)
    print(out.read().decode(errors="replace").rstrip())
    e = err.read().decode(errors="replace")
    if e.strip() and "[sudo]" not in e:
        print("STDERR:", e.rstrip())
c.close()

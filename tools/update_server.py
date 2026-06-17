import paramiko
from scp import SCPClient
import os
import tarfile
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load credentials from docs/Environment/credentials.md or hardcode for now
HOST = "100.125.63.77"
USER = "fathertkt"
PASS = "1234"
REMOTE_DIR = "prism-backend"

def progress(filename, size, sent):
    sys.stdout.write(f"\rUploading {filename}: {float(sent)/float(size)*100:.2f}%")
    sys.stdout.flush()

def filter_data(tarinfo):
    # EXCLUDE database and stateful directories to prevent overwriting production data
    exclude_paths = [
        f"{REMOTE_DIR}/data/postgres",
        f"{REMOTE_DIR}/data/synapse/media_store",
        f"{REMOTE_DIR}/data/synapse/homeserver.db",
        f"{REMOTE_DIR}/data/whatsapp/logs"
    ]
    for path in exclude_paths:
        if tarinfo.name.startswith(path):
            print(f"  [Skip] {tarinfo.name}")
            return None
    return tarinfo

def update_server():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {HOST}...")
        client.connect(hostname=HOST, username=USER, password=PASS)
        
        # 1. Archive local Backend folder
        print("Archiving local Backend folder (Excluding databases)...")
        with tarfile.open("backend_update.tar", "w") as tar:
            tar.add("Backend", arcname=REMOTE_DIR, filter=filter_data)
        
        # 2. Upload to server
        print("Uploading to server...")
        with SCPClient(client.get_transport(), progress=progress) as scp:
            scp.put("backend_update.tar", "backend_update.tar")
        print("\nUpload complete.")
        
        # 3. Extract and Run Setup
        print("Extracting and running setup on server (requires sudo)...")
        # We use 'sudo tar' to overwrite files owned by root/docker
        commands = [
            f"echo {PASS} | sudo -S tar -xf backend_update.tar",
            f"cd {REMOTE_DIR} && echo {PASS} | sudo -S sed -i 's/\\r$//' *.sh",
            f"cd {REMOTE_DIR} && echo {PASS} | sudo -S chmod +x *.sh && echo {PASS} | sudo -S ./setup-prism.sh",
            f"rm backend_update.tar"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            
            # Read output and error
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                print(f"FAILED: {cmd}")
                print(f"STDERR: {err}")
                return # Stop if a command fails
            else:
                if out: print(out)
        
        # 4. Apply changes and start containers
        print("Starting all containers...")
        stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_DIR} && echo {PASS} | sudo -S docker compose up -d --remove-orphans")
        if stdout.channel.recv_exit_status() == 0:
            print("Containers updated and running.")
        else:
            print(f"FAILED to start containers: {stderr.read().decode()}")
        
        print("\nUpdate Successful!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()
        if os.path.exists("backend_update.tar"):
            os.remove("backend_update.tar")

if __name__ == "__main__":
    update_server()

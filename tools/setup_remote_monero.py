import paramiko

HP_HOST = "100.77.114.31"
HP_USER = "fatih"
HP_PASS = "V12_Abd!78"

RPI_HOST = "100.125.63.77"
RPI_USER = "fathertkt"
RPI_PASS = "1234"

DOCKER_COMPOSE_MONERO = """services:
  monerod:
    image: ghcr.io/sethforprivacy/simple-monerod:latest
    container_name: monero-node
    restart: unless-stopped
    volumes:
      - ./data:/home/monero/.bitmonero
    ports:
      - "18080:18080"
      - "18081:18081"
    command:
      - "--rpc-bind-ip=0.0.0.0"
      - "--rpc-bind-port=18081"
      - "--confirm-external-bind"
      - "--restricted-rpc"
      - "--no-igd"
      - "--enable-dns-blocklist"
      - "--prune-blockchain"
"""

def setup_hp_laptop():
    print(f"Connecting to HP Laptop ({HP_HOST})...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HP_HOST, username=HP_USER, password=HP_PASS)
        
        print("Creating directory structure...")
        client.exec_command("mkdir -p prism-monero/data")
        
        print("Writing docker-compose.yml...")
        sftp = client.open_sftp()
        with sftp.file("prism-monero/docker-compose.yml", "w") as f:
            f.write(DOCKER_COMPOSE_MONERO)
        sftp.close()
        
        print("Starting Monero node...")
        stdin, stdout, stderr = client.exec_command("cd prism-monero && docker-compose up -d")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("SUCCESS: Monero node started on HP Laptop")
        else:
            print(f"FAILURE: {stderr.read().decode()}")
            
    finally:
        client.close()

if __name__ == "__main__":
    setup_hp_laptop()

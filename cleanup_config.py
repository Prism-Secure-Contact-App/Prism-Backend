import os
import re

CONFIG_FILE = "./data/synapse/homeserver.yaml"

def main():
    if not os.path.exists(CONFIG_FILE):
        return

    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()

    new_lines = []
    in_appservice_block = False
    appservices_to_keep = [
        "- /data/appservice-whatsapp.yaml",
        "- /data/appservice-instagram.yaml"
    ]
    
    # We want to keep the header and the specific files we want
    for line in lines:
        stripped = line.strip()
        if stripped == "app_service_config_files:":
            in_appservice_block = True
            new_lines.append(line)
            continue
        
        if in_appservice_block:
            if stripped.startswith("- "):
                if stripped in appservices_to_keep:
                    new_lines.append(line)
                else:
                    print(f"🗑️ Removing old appservice: {stripped}")
                continue
            elif stripped == "" or line.startswith(" "):
                # Skip empty lines or indented lines that aren't appservices (rare)
                continue
            else:
                in_appservice_block = False
        
        new_lines.append(line)

    with open(CONFIG_FILE, "w") as f:
        f.writelines(new_lines)
    print("✅ homeserver.yaml cleaned up.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Generate bridgev2-format config for whatsapp bridge

whatsapp_config = """# Bridge v2 format
# This is a generated config for mautrix-whatsapp using bridgev2 framework

# Service settings
network:
  homeserver: "https://matrix.fathertkt.uk"
  homeserver_domain: "matrix.fathertkt.uk"

appservice:
  protocol: whatsapp
  bot:
    username: pwb-bot
    displayname: "WhatsApp Bridge Bot"
    avatar: "mxc://matrix.fathertkt.uk/bYrBOB"

# Database settings
database:
  type: postgres
  uri: "postgresql://synapse:1234@db:5432/whatsapp"

# Logging
logging:
  level: info

# WhatsApp specific settings
whatsapp:
  os_name: "Mautrix-WhatsApp bridge"
  browser_name: unknown
  
# Message settings
message:
  max_initial_sync: 20
  
# Provisioning
provisioning:
  shared_secret: "whatsapp_secret_123"
"""

meta_config = """# Bridge v2 format
# This is a generated config for mautrix-meta using bridgev2 framework

# Service settings
network:
  homeserver: "https://matrix.fathertkt.uk"
  homeserver_domain: "matrix.fathertkt.uk"

appservice:
  protocol: meta
  bot:
    username: pmb-bot
    displayname: "Meta Bridge Bot"
    avatar: "mxc://matrix.fathertkt.uk/bYrBOB"

# Database settings
database:
  type: postgres
  uri: "postgresql://synapse:1234@db:5432/meta"

# Logging
logging:
  level: info

# Meta specific settings (Instagram mode)
meta:
  mode: instagram
  
# Message settings
message:
  max_initial_sync: 20

# Provisioning
provisioning:
  shared_secret: "meta_secret_123"
"""

# Save templates
with open("whatsapp_config_template.yaml", "w") as f:
    f.write(whatsapp_config)

with open("meta_config_template.yaml", "w") as f:
    f.write(meta_config)

print("✅ Config templates created")
print(f"   whatsapp_config_template.yaml ({len(whatsapp_config)} bytes)")
print(f"   meta_config_template.yaml ({len(meta_config)} bytes)")

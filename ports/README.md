# Port Extractor

This script extracts all bound ports, and identifies which processes they are bound to and by which protocols. 
Notable addition is handling of docker containers. 

## Usage 

```bash
sudo python port_extractor.py
```

## Example Output

```bash
Port 22 (tcp, tcp6)
  [System] sshd (PID: 708)

Port 53 (tcp, tcp6)
  [System] pihole-FTL (PID: 58710)

Port 80 (tcp, tcp6)
  [System] lighttpd (PID: 809)

Port 4711 (tcp, tcp6)
  [System] pihole-FTL (PID: 58710)

Port 5335 (tcp)
  [System] unbound (PID: 712)

Port 6000 (tcp, tcp6)
  [Docker] authentik-server-1 (PID: 24851, 24858) [container port: 9000]

```


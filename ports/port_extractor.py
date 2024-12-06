#!/usr/bin/env python3
import sys
import subprocess
from collections import defaultdict

def get_netstat_output():
    """
    Run netstat command and return its output.
    """
    try:
        result = subprocess.run(['sudo', 'netstat', '-nltp'], 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            print("Error running netstat. Make sure you have sudo privileges.", 
                  file=sys.stderr)
            sys.exit(1)
        return result.stdout
    except FileNotFoundError:
        print("Error: netstat command not found. Please install net-tools package.", 
              file=sys.stderr)
        sys.exit(1)

def get_container_info(pid):
    """
    Get container name and port mapping for a given docker-proxy PID
    Returns tuple of (name, container_port)
    """
    try:
        # Get the port this docker-proxy is listening on
        ps_cmd = ['ps', '-o', 'args=', '-p', pid]
        ps_output = subprocess.run(ps_cmd, capture_output=True, text=True).stdout.strip()
        
        # Extract host port and container port from ps output
        args = ps_output.split()
        host_port = container_port = None
        for i, arg in enumerate(args):
            if arg == '-host-port' and i + 1 < len(args):
                host_port = args[i + 1]
            elif arg == '-container-port' and i + 1 < len(args):
                container_port = args[i + 1]
        
        if not (host_port and container_port):
            return 'unknown container', None

        # Get all running containers
        docker_cmd = ['docker', 'ps', '--format', '{{.Names}}\t{{.Ports}}']
        docker_output = subprocess.run(docker_cmd, capture_output=True, text=True).stdout.strip()
        
        # Look for container with matching port mapping
        for line in docker_output.splitlines():
            name, ports = line.split('\t')
            # Convert ports to a set of host:container mappings
            mappings = []
            for mapping in ports.split(', '):
                if '->' in mapping:
                    # Handle "0.0.0.0:8080->8080/tcp" format
                    host_part = mapping.split('->')[0]
                    container_part = mapping.split('->')[1]
                    if ':' in host_part:
                        mapped_host_port = host_part.split(':')[-1]
                        mapped_container_port = container_part.split('/')[0]
                        mappings.append((mapped_host_port, mapped_container_port))
            
            # Check if this container has our port mapping
            if (host_port, container_port) in mappings:
                return name, container_port
            
        return 'unknown container', None
    except Exception:
        return 'unknown container', None

def parse_process_info(process_str):
    """
    Parse the process information string from netstat output
    Returns tuple of (pid, name)
    """
    try:
        if '/' not in process_str:
            return None, None

        # Split on first slash
        pid, rest = process_str.split('/', 1)
        
        # For sshd and similar services, take everything before the colon
        name = rest.split(':')[0] if ':' in rest else rest
        
        return pid.strip(), name.strip()
    except Exception:
        return None, None

def extract_ports_and_services(netstat_output):
    """
    Extract unique ports and their associated services from netstat -nltp output.
    Groups multiple instances of the same port together.
    """
    port_services = {}
    
    # Skip the first two header lines
    for line in netstat_output.splitlines()[2:]:
        # Split only on whitespace, but limit to 6 splits to keep the last column intact
        parts = line.split(None, 6)
        if len(parts) < 7:
            continue
            
        protocol = parts[0]
        local_addr = parts[3]
        try:
            port = int(local_addr.split(':')[-1])
        except ValueError:
            continue

        # Get program name (last column)
        pid, name = parse_process_info(parts[6])
        if pid and name:
            # Check if it's a docker proxy
            if name == 'docker-proxy':
                service_type = 'docker'
                container_name, container_port = get_container_info(pid)
                name = container_name
            else:
                service_type = 'system'
                container_port = None
                
            # Create unique service key
            service_key = (port, name, service_type)
            
            # Update or create service entry
            if service_key not in port_services:
                port_services[service_key] = {
                    'port': port,
                    'name': name,
                    'type': service_type,
                    'pids': set(),
                    'protocols': set(),
                    'container_port': container_port
                }
            
            port_services[service_key]['pids'].add(pid)
            port_services[service_key]['protocols'].add(protocol)
    
    return port_services

def main():
    try:
        netstat_output = get_netstat_output()
        port_services = extract_ports_and_services(netstat_output)
        
        # Convert to list and sort by port number
        services_list = sorted(port_services.values(), key=lambda x: x['port'])
        
        # Print services
        for service in services_list:
            print(f"\nPort {service['port']} ({', '.join(sorted(service['protocols']))})")
            
            service_type = "[Docker]" if service['type'] == 'docker' else "[System]"
            pids = ", ".join(sorted(service['pids']))
            
            # Base output
            output = f"  {service_type} {service['name']} (PID: {pids})"
            
            # Add container port if different from host port
            if service['type'] == 'docker' and service['container_port'] and service['container_port'] != str(service['port']):
                output += f" [container port: {service['container_port']}]"
            
            print(output)
                
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

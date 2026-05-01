import subprocess

def check_vpn_active():
    try:
        cmd_vpn = ["powershell", "-Command", "Get-VpnConnection -ErrorAction SilentlyContinue | Where-Object { $_.ConnectionStatus -eq 'Connected' }"]
        res = subprocess.run(cmd_vpn, capture_output=True, text=True)
        print(f"VPN Connection Check Output: {repr(res.stdout.strip())}")
        
        keywords = "'VPN|TAP|TUN|WireGuard|PANGP|Cisco|AnyConnect|Pulse|Fortinet|Proton|Express|Nord|Surfshark|CyberGhost|Windscribe|PIA|TunnelBear|Mullvad|Hide.me|Vypr|TorGuard|IVPN'"
        cmd_adapter = ["powershell", "-Command", f"Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {{ $_.Status -eq 'Up' -and ($_.InterfaceDescription -match {keywords} -or $_.Name -match {keywords}) }}"]
        res2 = subprocess.run(cmd_adapter, capture_output=True, text=True)
        print(f"NetAdapter Check Output: {repr(res2.stdout.strip())}")
        
        if res.stdout.strip() or res2.stdout.strip():
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return True

print(f"Final Result: {check_vpn_active()}")

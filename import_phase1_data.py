"""
File: scripts/import_phase1_data.py
Purpose: Import Phase 1 data from router config and ARIN CSV
Version: 1.0.0
Author: DCMS Team
Date: 2025-01-16

Run this script to populate the database with:
- VLANs from router configuration
- Subnets mapped to VLANs
- ARIN IP ranges

Usage: python scripts/import_phase1_data.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models.vlan import VLAN, VLANSubnet, calculate_subnet_info
from models.ipam import IPRange
import re

# ========== ROUTER CONFIGURATION DATA ==========
ROUTER_CONFIG = """
vlan 2-14,17,30,90-94,100,111,199-217,300-301,1000,1199

interface Vlan2
   description Vlan2
   ip address 208.76.80.254/25
   ip address 199.58.178.1/25 secondary

interface Vlan3
   description Vlan3
   ip address 208.76.81.1/24

interface Vlan5
   description Vlan5
   ip address 208.76.82.1/25

interface Vlan6
   description Vlan6
   ip address 208.76.82.254/25
   ip address 199.58.178.254/25 secondary

interface Vlan7
   description Vlan7
   ip address 208.76.83.1/25

interface Vlan8
   description Vlan8
   ip address 208.76.83.254/25

interface Vlan9
   description Vlan9
   ip address 208.76.84.1/25
   ip address 199.58.177.1/25 secondary

interface Vlan10
   description Vlan10
   ip address 208.76.84.254/25
   ip address 10.77.77.1/24 secondary

interface Vlan11
   description Vlan11
   ip address 208.76.85.1/25

interface Vlan12
   description Vlan12
   ip address 208.76.85.254/25
   ip address 199.58.179.1/24 secondary

interface Vlan13
   description Vlan13
   ip address 208.76.86.1/25

interface Vlan14
   description Vlan14
   ip address 208.76.87.1/24

interface Vlan17
   description Vlan17
   ip address 208.76.86.129/25

interface Vlan90
   description Vlan90
   ip address 199.102.70.1/24

interface Vlan91
   description Vlan91
   ip address 208.79.210.1/24

interface Vlan92
   description Vlan92
   ip address 208.79.212.161/27

interface Vlan93
   description Vlan93
   ip address 208.92.219.225/27

interface Vlan94
   description Vlan94
   ip address 208.76.208.1/27

interface Vlan100
   description Vlan100
   ip address 198.38.76.1/22

interface Vlan111
   description Vlan111
   ip address 208.76.80.3/25
   ip address 199.58.176.254/25 secondary
   ip address 199.58.177.254/25 secondary

interface Vlan201
   description vlan 201
   ip address 66.51.159.1/29

interface Vlan202
   description vlan202
   ip address 66.51.159.17/28

interface Vlan203
   description vlan203
   ip address 66.51.159.9/29
   ip address 66.51.159.65/29 secondary

interface Vlan204
   description vlan 204
   ip address 66.51.159.33/28

interface Vlan205
   description vlan205
   ip address 66.51.159.49/28

interface Vlan206
   description vlan206
   ip address 66.51.159.73/29

interface Vlan207
   description vlan 207
   ip address 66.51.159.81/29

interface Vlan208
   description vlan208
   ip address 66.51.159.89/29

interface Vlan209
   description colo 51456
   ip address 66.51.159.97/29

interface Vlan210
   description vlan 210
   ip address 66.51.159.105/29

interface Vlan211
   description vlan211
   ip address 66.51.159.113/29

interface Vlan212
   description colo51451
   ip address 66.51.159.121/29

interface Vlan213
   description vlan213
   ip address 66.51.159.129/28

interface Vlan214
   description vlan 214
   ip address 66.51.159.145/28

interface Vlan215
   description vlan 215
   ip address 66.51.159.161/29

interface Vlan216
   description vlan216
   ip address 66.51.159.169/29

interface Vlan217
   description colo51526
   ip address 66.51.159.177/29

interface Vlan301
   description Vlan TCH Private Network
   ip address 10.10.6.200/22

interface Vlan1000
   description MNGMT_Vlan
   ip address 10.0.0.1/24
"""

# ========== ARIN ALLOCATIONS DATA ==========
ARIN_DATA = """Net Handle\tNet Range\tNet Type\tNet Name\tOrg ID\tOrg Name\tParent Net\tParent Org\tRSA/LRSA
NET6-2605-89C0-1\t2605:89C0::/32\tDA\tTCH-IPV6-V1\tTHL-15\tTotalChoice Hosting LLC\tNET6-2600-1\tARIN\tYes
NET-66-51-159-0-1\t66.51.159.0/25\tS\tTOTALCHOICE-COLOCATION\tTHL-15\tTotalChoice Hosting LLC\tNET-66-51-144-0-1\tNETIN-6\tYes
NET-66-51-159-128-1\t66.51.159.128/26\tS\t123NET-BLK-066051159128-26\tTHL-15\tTotalChoice Hosting LLC\tNET-66-51-144-0-1\tNETIN-6\tYes
NET-198-38-76-0-1\t198.38.76.0/22\tDA\tTCH-IPV4-V3\tTHL-15\tTotalChoice Hosting LLC\tNET-198-0-0-0-0\tVR-ARIN\tYes
NET-199-58-176-0-1\t199.58.176.0/22\tDA\tTCH-IPV4-V2\tTHL-15\tTotalChoice Hosting LLC\tNET-199-0-0-0-0\tARIN\tYes
NET-208-76-80-0-1\t208.76.80.0/21\tDA\tTCH-IPV4-V1\tTHL-15\tTotalChoice Hosting LLC\tNET-208-0-0-0-0\tARIN\tYes"""

def determine_vlan_purpose(vlan_id, subnets):
    """Determine VLAN purpose based on ID and subnet ranges"""
    # Colocation VLANs (201-217 using 66.x space)
    if 201 <= vlan_id <= 217:
        return 'colocation'
    
    # Check subnet ranges
    for subnet in subnets:
        if subnet.startswith('66.51.159'):
            return 'colocation'
        elif subnet.startswith('10.'):
            if vlan_id == 1000:
                return 'management'
            return 'private'
    
    # Special cases
    if vlan_id == 1000:
        return 'management'
    elif vlan_id in [300, 301]:
        return 'private'
    
    # Default to infrastructure
    return 'infrastructure'

def parse_vlan_interfaces():
    """Parse VLAN interface configurations from router config"""
    vlans_data = {}
    
    # Parse each interface Vlan block
    interface_blocks = re.findall(
        r'interface Vlan(\d+)\n((?:   .*\n)*)',
        ROUTER_CONFIG
    )
    
    for vlan_id, config_block in interface_blocks:
        vlan_id = int(vlan_id)
        
        # Extract description
        desc_match = re.search(r'description (.+)', config_block)
        description = desc_match.group(1) if desc_match else f'Vlan{vlan_id}'
        
        # Extract IP addresses (primary and secondary)
        subnets = []
        ip_lines = re.findall(r'ip address ([\d\.]+)/(\d+)(\s+secondary)?', config_block)
        
        for idx, (ip, cidr, secondary) in enumerate(ip_lines):
            is_primary = not bool(secondary)
            subnet_cidr = f"{ip}/{cidr}"
            
            # Calculate network address from gateway IP
            import ipaddress
            network = ipaddress.IPv4Network(subnet_cidr, strict=False)
            
            subnets.append({
                'subnet': str(network),
                'gateway': ip,
                'is_primary': is_primary
            })
        
        vlans_data[vlan_id] = {
            'description': description,
            'subnets': subnets
        }
    
    return vlans_data

def import_vlans():
    """Import VLANs and subnets into database"""
    print("\n========== IMPORTING VLANs FROM ROUTER CONFIG ==========\n")
    
    vlans_data = parse_vlan_interfaces()
    vlans_created = 0
    subnets_created = 0
    
    with app.app_context():
        for vlan_id, vlan_info in sorted(vlans_data.items()):
            # Check if VLAN already exists
            existing_vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
            
            if existing_vlan:
                print(f"VLAN {vlan_id} already exists, skipping...")
                continue
            
            # Determine purpose based on VLAN ID and subnets
            subnet_addresses = [s['subnet'] for s in vlan_info['subnets']]
            purpose = determine_vlan_purpose(vlan_id, subnet_addresses)
            
            # Create VLAN
            vlan = VLAN(
                vlan_id=vlan_id,
                name=f"Vlan{vlan_id}",
                description=vlan_info['description'],
                purpose=purpose,
                status='active'
            )
            db.session.add(vlan)
            db.session.flush()  # Get the ID
            vlans_created += 1
            
            print(f"Created VLAN {vlan_id} ({vlan_info['description']}) - Purpose: {purpose}")
            
            # Add subnets
            for subnet_data in vlan_info['subnets']:
                subnet_info = calculate_subnet_info(subnet_data['subnet'])
                
                subnet = VLANSubnet(
                    vlan_id=vlan.id,
                    subnet=subnet_data['subnet'],
                    gateway=subnet_data['gateway'],
                    is_primary=subnet_data['is_primary'],
                    network_address=subnet_info['network_address'],
                    broadcast_address=subnet_info['broadcast_address'],
                    cidr=subnet_info['cidr'],
                    total_ips=subnet_info['total_ips'],
                    usable_ips=subnet_info['usable_ips']
                )
                db.session.add(subnet)
                subnets_created += 1
                
                primary = "Primary" if subnet_data['is_primary'] else "Secondary"
                print(f"  - {primary}: {subnet_data['subnet']} (GW: {subnet_data['gateway']}) - {subnet_info['total_ips']} IPs")
        
        db.session.commit()
        print(f"\n✓ Import complete: {vlans_created} VLANs and {subnets_created} subnets created")

def import_arin_ranges():
    """Import ARIN IP ranges"""
    print("\n========== IMPORTING ARIN ALLOCATIONS ==========\n")
    
    ranges_created = 0
    
    with app.app_context():
        # Parse ARIN data (tab-separated)
        lines = ARIN_DATA.strip().split('\n')
        headers = lines[0].split('\t')
        
        for line in lines[1:]:  # Skip header
            values = line.split('\t')
            
            # Extract relevant fields
            net_range = values[1]  # e.g., "66.51.159.0/25"
            net_type = values[2]   # e.g., "DA" or "S"
            net_name = values[3]    # e.g., "TOTALCHOICE-COLOCATION"
            
            # Skip IPv6 for Phase 1
            if ':' in net_range:
                print(f"Skipping IPv6 range: {net_range}")
                continue
            
            # Parse network and CIDR
            if '/' in net_range:
                network, cidr = net_range.split('/')
                cidr = int(cidr)
            else:
                continue
            
            # Check if range already exists
            existing_range = IPRange.query.filter_by(
                network=network,
                cidr=cidr
            ).first()
            
            if existing_range:
                print(f"Range {net_range} already exists, skipping...")
                continue
            
            # Determine network type based on IP
            if network.startswith('66.51.159'):
                network_type = 'colocation'
            elif network.startswith('10.'):
                network_type = 'private'
            else:
                network_type = 'public'
            
            # Calculate IP counts
            total_ips = 2 ** (32 - cidr)
            usable_ips = total_ips - 2 if total_ips > 2 else total_ips
            
            # Create IP range
            ip_range = IPRange(
                name=net_name,
                network=network,
                cidr=cidr,
                network_type=network_type,
                provider='ARIN',
                description=f"ARIN Allocation - Type: {net_type}",
                total_ips=total_ips,
                usable_ips=usable_ips
            )
            db.session.add(ip_range)
            ranges_created += 1
            
            print(f"Created IP Range: {net_range} ({net_name}) - {network_type} - {total_ips} IPs")
        
        db.session.commit()
        print(f"\n✓ Import complete: {ranges_created} IP ranges created")

def main():
    """Main import function"""
    print("=" * 60)
    print("PHASE 1 IPAM DATA IMPORT")
    print("=" * 60)
    
    # Import VLANs from router config
    import_vlans()
    
    # Import ARIN ranges
    import_arin_ranges()
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. View all VLANs at: /vlans/")
    print("2. View IP ranges at: /ipam/ranges")
    print("3. Start Phase 2: Capacity Tracking")

if __name__ == "__main__":
    main()
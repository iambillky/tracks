"""
File: routes/vlans.py
Purpose: Route handlers for VLAN management in Phase 1 IPAM
Version: 1.0.0
Author: DCMS Team
Date: 2025-01-16

Routes for:
- Displaying all VLANs with their subnets
- Importing router configurations
- Importing ARIN allocations
- Managing VLANs and subnets

Revision History:
- v1.0.0: Initial creation for Phase 1 IPAM Foundation
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.datacenter import db, DataCenter
from models.vlan import VLAN, VLANSubnet, calculate_subnet_info
from models.ipam import IPRange
from forms.vlan_forms import (
    VLANForm, VLANSubnetForm, RouterConfigImportForm, 
    ARINImportForm, VLANSearchForm
)
from sqlalchemy import or_, and_, func
import re
import csv
import io

# ========== BLUEPRINT INITIALIZATION ==========

vlans_bp = Blueprint('vlans', __name__, url_prefix='/vlans')

# ========== MAIN VIEWS ==========

@vlans_bp.route('/')
def index():
    """
    Main VLAN dashboard
    Shows all VLANs with their associated subnets
    """
    # Initialize search form
    search_form = VLANSearchForm()
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    purpose = request.args.get('purpose', 'all')
    status = request.args.get('status', 'all')
    has_secondary = request.args.get('has_secondary', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Build query
    query = VLAN.query
    
    # Apply search filter
    if search_query:
        search_pattern = f'%{search_query}%'
        # Search in VLAN ID, name, description, and subnets
        query = query.filter(or_(
            VLAN.vlan_id.cast(db.String).like(search_pattern),
            VLAN.name.like(search_pattern),
            VLAN.description.like(search_pattern)
        ))
    
    # Apply filters
    if purpose != 'all':
        query = query.filter_by(purpose=purpose)
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Filter by secondary subnets
    if has_secondary == 'yes':
        # VLANs with more than one subnet
        query = query.join(VLANSubnet).group_by(VLAN.id).having(func.count(VLANSubnet.id) > 1)
    elif has_secondary == 'no':
        # VLANs with exactly one subnet
        query = query.join(VLANSubnet).group_by(VLAN.id).having(func.count(VLANSubnet.id) == 1)
    
    # Order by VLAN ID
    query = query.order_by(VLAN.vlan_id)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    vlans = pagination.items
    
    # Get statistics
    total_vlans = VLAN.query.count()
    infra_vlans = VLAN.query.filter_by(purpose='infrastructure').count()
    colo_vlans = VLAN.query.filter_by(purpose='colocation').count()
    total_subnets = VLANSubnet.query.count()
    
    return render_template('vlans/index.html',
                         vlans=vlans,
                         pagination=pagination,
                         search_form=search_form,
                         total_vlans=total_vlans,
                         infra_vlans=infra_vlans,
                         colo_vlans=colo_vlans,
                         total_subnets=total_subnets)

# ========== ROUTER CONFIG IMPORT ==========

@vlans_bp.route('/import-router-config', methods=['GET', 'POST'])
def import_router_config():
    """
    Import VLANs and subnet mappings from router configuration
    """
    form = RouterConfigImportForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        config_text = form.config_text.data
        datacenter_id = form.datacenter_id.data if form.datacenter_id.data else None
        overwrite = form.overwrite.data
        
        # Parse the router configuration
        parsed_data = parse_router_config(config_text)
        
        # Import statistics
        vlans_created = 0
        vlans_updated = 0
        subnets_created = 0
        errors = []
        
        # Process each VLAN
        for vlan_data in parsed_data['vlans']:
            vlan_id = vlan_data['vlan_id']
            
            # Check if VLAN exists
            existing_vlan = VLAN.query.filter_by(vlan_id=vlan_id).first()
            
            if existing_vlan and not overwrite:
                # Skip existing VLANs if not overwriting
                continue
            
            if existing_vlan:
                # Update existing VLAN
                vlan = existing_vlan
                vlan.name = vlan_data['name']
                vlan.description = vlan_data.get('description', '')
                vlan.purpose = determine_vlan_purpose(vlan_id, vlan_data.get('subnets', []))
                vlans_updated += 1
            else:
                # Create new VLAN
                vlan = VLAN(
                    vlan_id=vlan_id,
                    name=vlan_data['name'],
                    description=vlan_data.get('description', ''),
                    purpose=determine_vlan_purpose(vlan_id, vlan_data.get('subnets', [])),
                    status='active',
                    datacenter_id=datacenter_id
                )
                db.session.add(vlan)
                vlans_created += 1
            
            db.session.flush()  # Get the VLAN ID for subnet creation
            
            # Process subnets
            for subnet_data in vlan_data.get('subnets', []):
                # Check if subnet already exists for this VLAN
                existing_subnet = VLANSubnet.query.filter_by(
                    vlan_id=vlan.id,
                    subnet=subnet_data['subnet']
                ).first()
                
                if not existing_subnet:
                    # Calculate subnet info
                    subnet_info = calculate_subnet_info(subnet_data['subnet'])
                    
                    # Create new subnet
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
        
        db.session.commit()
        
        # Flash results
        flash(f'Import complete: {vlans_created} VLANs created, {vlans_updated} updated, {subnets_created} subnets added', 'success')
        if errors:
            for error in errors[:5]:
                flash(error, 'warning')
        
        return redirect(url_for('vlans.index'))
    
    return render_template('vlans/import_router_config.html', form=form)

# ========== ARIN CSV IMPORT ==========

@vlans_bp.route('/import-arin', methods=['GET', 'POST'])
def import_arin():
    """
    Import ARIN allocations from CSV
    """
    form = ARINImportForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        csv_data = form.csv_data.data
        datacenter_id = form.datacenter_id.data if form.datacenter_id.data else None
        create_vlans = form.create_vlans.data
        
        # Parse CSV data
        ranges_created = 0
        vlans_created = 0
        errors = []
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_data), delimiter='\t')
        
        for row in csv_reader:
            try:
                # Extract data from CSV row
                net_range = row.get('Net Range', '').strip()
                net_name = row.get('Net Name', '').strip()
                net_type = row.get('Net Type', '').strip()
                
                if not net_range:
                    continue
                
                # Parse network and CIDR
                if '/' in net_range:
                    network, cidr = net_range.split('/')
                    cidr = int(cidr)
                else:
                    continue
                
                # Determine network type based on IP range
                if network.startswith('66.51.159'):
                    network_type = 'colocation'
                    # Auto-create VLAN for colo ranges if requested
                    if create_vlans:
                        # Extract VLAN ID from the range (simplified logic)
                        # This would need more sophisticated mapping in production
                        pass
                elif network.startswith('10.'):
                    network_type = 'private'
                else:
                    network_type = 'public'
                
                # Check if range already exists
                existing_range = IPRange.query.filter_by(
                    network=network,
                    cidr=cidr
                ).first()
                
                if not existing_range:
                    # Calculate IP counts
                    total_ips = 2 ** (32 - cidr)
                    usable_ips = total_ips - 2 if total_ips > 2 else total_ips
                    
                    # Create IP range
                    ip_range = IPRange(
                        name=net_name or f'ARIN-{network}/{cidr}',
                        network=network,
                        cidr=cidr,
                        network_type=network_type,
                        datacenter_id=datacenter_id,
                        provider='ARIN',
                        description=f'Net Type: {net_type}',
                        total_ips=total_ips,
                        usable_ips=usable_ips
                    )
                    db.session.add(ip_range)
                    ranges_created += 1
                    
            except Exception as e:
                errors.append(f'Error processing row: {str(e)}')
        
        db.session.commit()
        
        # Flash results
        flash(f'Import complete: {ranges_created} IP ranges imported', 'success')
        if errors:
            for error in errors[:5]:
                flash(error, 'warning')
        
        return redirect(url_for('ipam.ranges'))
    
    return render_template('vlans/import_arin.html', form=form)

# ========== VLAN CRUD OPERATIONS ==========

# UPDATE THIS SECTION IN routes/vlans.py

@vlans_bp.route('/add', methods=['GET', 'POST'])
def add_vlan():
    """Add a new VLAN with subnet configuration"""
    form = VLANForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        # Create the VLAN
        vlan = VLAN(
            vlan_id=form.vlan_id.data,
            name=form.name.data,
            description=form.description.data,
            purpose=form.purpose.data,
            status=form.status.data,
            datacenter_id=form.datacenter_id.data if form.datacenter_id.data else None,
            notes=form.notes.data
        )
        
        db.session.add(vlan)
        db.session.flush()  # Get the VLAN ID without committing
        
        # Handle primary subnet (required)
        primary_subnet = request.form.get('primary_subnet')
        primary_gateway = request.form.get('primary_gateway')
        
        if primary_subnet and primary_gateway:
            # Calculate subnet info
            subnet_info = calculate_subnet_info(primary_subnet)
            
            # Create primary subnet
            primary = VLANSubnet(
                vlan_id=vlan.id,
                subnet=primary_subnet,
                gateway=primary_gateway,
                is_primary=True,
                network_address=subnet_info['network_address'],
                broadcast_address=subnet_info['broadcast_address'],
                cidr=subnet_info['cidr'],
                total_ips=subnet_info['total_ips'],
                usable_ips=subnet_info['usable_ips'],
                assigned_count=0,
                reserved_count=0
            )
            db.session.add(primary)
        else:
            flash('Primary subnet configuration is required!', 'error')
            db.session.rollback()
            return render_template('vlans/add_vlan.html', form=form)
        
        # Handle secondary subnet (optional)
        secondary_subnet = request.form.get('secondary_subnet')
        secondary_gateway = request.form.get('secondary_gateway')
        
        if secondary_subnet and secondary_gateway:
            # Calculate subnet info
            subnet_info = calculate_subnet_info(secondary_subnet)
            
            # Create secondary subnet
            secondary = VLANSubnet(
                vlan_id=vlan.id,
                subnet=secondary_subnet,
                gateway=secondary_gateway,
                is_primary=False,
                network_address=subnet_info['network_address'],
                broadcast_address=subnet_info['broadcast_address'],
                cidr=subnet_info['cidr'],
                total_ips=subnet_info['total_ips'],
                usable_ips=subnet_info['usable_ips'],
                assigned_count=0,
                reserved_count=0
            )
            db.session.add(secondary)
        
        # Commit everything
        db.session.commit()
        
        # Count subnets for success message
        subnet_count = 1 if primary_subnet else 0
        subnet_count += 1 if secondary_subnet else 0
        
        flash(f'VLAN {vlan.vlan_id} ({vlan.name}) created with {subnet_count} subnet(s)!', 'success')
        return redirect(url_for('vlans.view_vlan', vlan_id=vlan.id))
    
    return render_template('vlans/add_vlan.html', form=form)

@vlans_bp.route('/vlan/<int:vlan_id>')
def view_vlan(vlan_id):
    """View VLAN details with all subnets"""
    vlan = VLAN.query.get_or_404(vlan_id)
    
    # Get IP statistics for each subnet
    subnet_stats = []
    for subnet in vlan.subnets:
        subnet_stats.append({
            'subnet': subnet,
            'utilization': subnet.utilization_percent,
            'available': subnet.available_count
        })
    
    return render_template('vlans/view_vlan.html', 
                         vlan=vlan, 
                         subnet_stats=subnet_stats)

@vlans_bp.route('/vlan/<int:vlan_id>/add-subnet', methods=['GET', 'POST'])
def add_subnet(vlan_id):
    """Add a subnet to a VLAN"""
    vlan = VLAN.query.get_or_404(vlan_id)
    form = VLANSubnetForm()
    
    if form.validate_on_submit():
        # Calculate subnet info
        subnet_info = calculate_subnet_info(form.subnet.data)
        
        # Create subnet
        subnet = VLANSubnet(
            vlan_id=vlan.id,
            subnet=form.subnet.data,
            gateway=form.gateway.data,
            is_primary=form.is_primary.data,
            network_address=subnet_info['network_address'],
            broadcast_address=subnet_info['broadcast_address'],
            cidr=subnet_info['cidr'],
            total_ips=subnet_info['total_ips'],
            usable_ips=subnet_info['usable_ips'],
            notes=form.notes.data
        )
        
        db.session.add(subnet)
        db.session.commit()
        
        flash(f'Subnet {subnet.subnet} added to VLAN {vlan.vlan_id}!', 'success')
        return redirect(url_for('vlans.view_vlan', vlan_id=vlan.id))
    
    return render_template('vlans/add_subnet.html', form=form, vlan=vlan)

# ========== HELPER FUNCTIONS ==========

def parse_router_config(config_text):
    """
    Parse router configuration to extract VLAN and subnet information
    """
    vlans = []
    vlan_interfaces = {}
    
    # Extract VLAN list from "vlan X-Y,Z" line
    vlan_list_match = re.search(r'^vlan\s+([\d,\-\s]+)$', config_text, re.MULTILINE)
    if vlan_list_match:
        vlan_str = vlan_list_match.group(1)
        # Parse ranges and individual VLANs
        for part in vlan_str.split(','):
            part = part.strip()
            if '-' in part:
                # Range of VLANs
                start, end = part.split('-')
                for vid in range(int(start), int(end) + 1):
                    vlans.append({'vlan_id': vid, 'name': f'Vlan{vid}'})
            else:
                # Single VLAN
                vlans.append({'vlan_id': int(part), 'name': f'Vlan{part}'})
    
    # Extract VLAN interface configurations
    interface_pattern = r'^interface Vlan(\d+)\n(?:.*\n)*?(?=^interface|\Z)'
    
    for match in re.finditer(interface_pattern, config_text, re.MULTILINE):
        interface_block = match.group(0)
        vlan_id = int(match.group(1))
        
        # Extract description
        desc_match = re.search(r'^\s+description\s+(.+)$', interface_block, re.MULTILINE)
        description = desc_match.group(1) if desc_match else f'Vlan{vlan_id}'
        
        # Extract IP addresses (primary and secondary)
        subnets = []
        ip_pattern = r'^\s+ip address\s+([\d\.]+)\s+([\d\.]+)(?:\s+secondary)?$'
        
        ip_matches = re.finditer(ip_pattern, interface_block, re.MULTILINE)
        for idx, ip_match in enumerate(ip_matches):
            ip = ip_match.group(1)
            mask = ip_match.group(2)
            is_secondary = 'secondary' in ip_match.group(0)
            
            # Convert subnet mask to CIDR
            cidr = mask_to_cidr(mask)
            network = get_network_address(ip, cidr)
            
            subnets.append({
                'subnet': f'{network}/{cidr}',
                'gateway': ip,
                'is_primary': not is_secondary
            })
        
        # Find the VLAN in our list and add interface info
        for vlan in vlans:
            if vlan['vlan_id'] == vlan_id:
                vlan['description'] = description
                vlan['subnets'] = subnets
                break
    
    return {'vlans': vlans}

def mask_to_cidr(mask):
    """Convert subnet mask to CIDR notation"""
    return sum(bin(int(x)).count('1') for x in mask.split('.'))

def get_network_address(ip, cidr):
    """Get network address from IP and CIDR"""
    # Simple implementation - would use ipaddress module in production
    ip_parts = [int(x) for x in ip.split('.')]
    mask = (0xffffffff << (32 - cidr)) & 0xffffffff
    
    network_int = (ip_parts[0] << 24) + (ip_parts[1] << 16) + (ip_parts[2] << 8) + ip_parts[3]
    network_int = network_int & mask
    
    return '.'.join([
        str((network_int >> 24) & 0xff),
        str((network_int >> 16) & 0xff),
        str((network_int >> 8) & 0xff),
        str(network_int & 0xff)
    ])

def determine_vlan_purpose(vlan_id, subnets):
    """Determine VLAN purpose based on VLAN ID and subnets"""
    # Colocation VLANs (201-217 using 66.x space)
    if 201 <= vlan_id <= 217:
        return 'colocation'
    
    # Check subnet ranges
    for subnet in subnets:
        if subnet.get('subnet', '').startswith('66.51.159'):
            return 'colocation'
        elif subnet.get('subnet', '').startswith('10.'):
            return 'private'
    
    # Management VLANs
    if vlan_id == 1000:
        return 'management'
    
    # Private VLANs
    if vlan_id in [301, 300]:
        return 'private'
    
    # Default to infrastructure
    return 'infrastructure'

@vlans_bp.route('/delete/<int:vlan_id>', methods=['POST'])
def delete_vlan(vlan_id):
    """Delete a VLAN and all its associated subnets"""
    vlan = VLAN.query.get_or_404(vlan_id)
    
    # Store info for flash message
    vlan_number = vlan.vlan_id
    vlan_name = vlan.name
    subnet_count = len(vlan.subnets)
    
    try:
        # The subnets will be deleted automatically due to cascade='all, delete-orphan' 
        # in the VLAN model relationship
        db.session.delete(vlan)
        db.session.commit()
        
        flash(f'VLAN {vlan_number} ({vlan_name}) and {subnet_count} subnet(s) deleted successfully!', 'success')
        return redirect(url_for('vlans.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting VLAN {vlan_number}: {str(e)}', 'error')
        return redirect(url_for('vlans.view_vlan', vlan_id=vlan_id))
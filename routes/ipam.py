"""
File: routes/ipam.py
Purpose: Route handlers for IP Address Management (IPAM)
Version: 1.0.0
Author: DCMS Team
Created: 2025-01-14

Revision History:
- v1.0.0: Initial creation with basic CRUD operations for IPs
         List view with filtering, add/edit/delete IPs
         Bulk import functionality
         IP range management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.datacenter import db, DataCenter
from models.network_device import NetworkDevice
from models.ipam import IPAddress, IPRange, validate_ip_address
from forms.ipam_forms import (
    IPAddressForm, QuickIPAddForm, BulkIPImportForm, 
    IPRangeForm, IPSearchForm
)
from sqlalchemy import or_, and_, func
import csv
import io

# ========== BLUEPRINT INITIALIZATION ==========

ipam_bp = Blueprint('ipam', __name__, url_prefix='/ipam')

# ========== MAIN VIEWS ==========

@ipam_bp.route('/')
def index():
    """
    Main IPAM dashboard
    Shows IP addresses with filtering and search
    """
    # Initialize search form
    search_form = IPSearchForm()
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    network_type = request.args.get('network_type', 'all')
    ip_type = request.args.get('ip_type', 'all')
    status = request.args.get('status', 'all')
    datacenter_id = request.args.get('datacenter_id', 'all')
    assignment = request.args.get('assignment', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query
    query = IPAddress.query
    
    # Apply search filter
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(or_(
            IPAddress.ip_address.like(search_pattern),
            IPAddress.dns_name.like(search_pattern),
            IPAddress.description.like(search_pattern)
        ))
    
    # Apply filters
    if network_type != 'all':
        query = query.filter_by(network_type=network_type)
    if ip_type != 'all':
        query = query.filter_by(ip_type=ip_type)
    if status != 'all':
        query = query.filter_by(status=status)
    if datacenter_id != 'all':
        query = query.filter_by(datacenter_id=int(datacenter_id))
    
    # Assignment filter
    if assignment == 'assigned':
        query = query.filter(IPAddress.assigned_to_type.isnot(None))
    elif assignment == 'unassigned':
        query = query.filter(IPAddress.assigned_to_type.is_(None))
    
    # Order by IP address (this won't be perfect for IPs but good enough for Phase 1)
    query = query.order_by(IPAddress.network_type, IPAddress.ip_address)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    ips = pagination.items
    
    # Get statistics
    total_ips = IPAddress.query.count()
    assigned_ips = IPAddress.query.filter(IPAddress.assigned_to_type.isnot(None)).count()
    available_ips = IPAddress.query.filter_by(status='available').count()
    reserved_ips = IPAddress.query.filter_by(status='reserved').count()
    
    # Get IP ranges
    ranges = IPRange.query.order_by(IPRange.network_type, IPRange.network).all()
    
    # Get datacenters for filter dropdown
    datacenters = DataCenter.query.order_by(DataCenter.code).all()
    
    # Calculate utilization
    utilization = round((assigned_ips / total_ips * 100) if total_ips > 0 else 0, 1)
    
    return render_template('ipam/index.html',
                         ips=ips,
                         pagination=pagination,
                         ranges=ranges,
                         search_form=search_form,
                         datacenters=datacenters,
                         total_ips=total_ips,
                         assigned_ips=assigned_ips,
                         available_ips=available_ips,
                         reserved_ips=reserved_ips,
                         utilization=utilization,
                         current_filters={
                             'search': search_query,
                             'network_type': network_type,
                             'ip_type': ip_type,
                             'status': status,
                             'datacenter_id': datacenter_id,
                             'assignment': assignment
                         })

# ========== IP ADDRESS OPERATIONS ==========

@ipam_bp.route('/ip/add', methods=['GET', 'POST'])
def add_ip():
    """Add a new IP address"""
    form = IPAddressForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        # Create new IP
        ip = IPAddress(
            ip_address=form.ip_address.data,
            version=4,  # Default to IPv4 for now
            ip_type=form.ip_type.data,
            network_type=form.network_type.data,
            vlan_id=form.vlan_id.data if form.vlan_id.data else None,
            status=form.status.data,
            datacenter_id=form.datacenter_id.data if form.datacenter_id.data else None,
            dns_name=form.dns_name.data,
            description=form.description.data,
            notes=form.notes.data
        )
        
        db.session.add(ip)
        db.session.commit()
        
        flash(f'IP address {ip.ip_address} added successfully!', 'success')
        return redirect(url_for('ipam.index'))
    
    return render_template('ipam/add_ip.html', form=form)

@ipam_bp.route('/ip/edit/<int:ip_id>', methods=['GET', 'POST'])
def edit_ip(ip_id):
    """Edit an existing IP address"""
    ip = IPAddress.query.get_or_404(ip_id)
    form = IPAddressForm(obj=ip)
    form.ip_id.data = ip_id  # Set the hidden field for validation
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        # Update IP
        ip.ip_address = form.ip_address.data
        ip.ip_type = form.ip_type.data
        ip.network_type = form.network_type.data
        ip.vlan_id = form.vlan_id.data if form.vlan_id.data else None
        ip.status = form.status.data
        ip.datacenter_id = form.datacenter_id.data if form.datacenter_id.data else None
        ip.dns_name = form.dns_name.data
        ip.description = form.description.data
        ip.notes = form.notes.data
        
        db.session.commit()
        
        flash(f'IP address {ip.ip_address} updated!', 'success')
        return redirect(url_for('ipam.index'))
    
    return render_template('ipam/edit_ip.html', form=form, ip=ip)

@ipam_bp.route('/ip/delete/<int:ip_id>', methods=['POST'])
def delete_ip(ip_id):
    """Delete an IP address"""
    ip = IPAddress.query.get_or_404(ip_id)
    
    # Check if IP is assigned
    if ip.is_assigned:
        flash(f'Cannot delete {ip.ip_address} - it is currently assigned to {ip.assigned_device_name}', 'error')
    else:
        ip_addr = ip.ip_address
        db.session.delete(ip)
        db.session.commit()
        flash(f'IP address {ip_addr} deleted!', 'success')
    
    return redirect(url_for('ipam.index'))

@ipam_bp.route('/ip/quick-add', methods=['POST'])
def quick_add_ip():
    """Quick add IP via modal/AJAX"""
    form = QuickIPAddForm()
    
    if form.validate_on_submit():
        ip = IPAddress(
            ip_address=form.ip_address.data,
            version=4,
            ip_type=form.ip_type.data,
            network_type=form.network_type.data,
            description=form.description.data,
            status='available'
        )
        
        db.session.add(ip)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'IP {ip.ip_address} added successfully!',
            'ip': {
                'id': ip.id,
                'ip_address': ip.ip_address,
                'type': ip.ip_type,
                'network': ip.network_type
            }
        })
    
    return jsonify({
        'success': False,
        'errors': form.errors
    })

# ========== BULK OPERATIONS ==========

@ipam_bp.route('/bulk-import', methods=['GET', 'POST'])
def bulk_import():
    """Bulk import IP addresses"""
    form = BulkIPImportForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        import_data = form.import_data.data
        lines = import_data.strip().split('\n')
        
        imported = 0
        skipped = 0
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Parse line (CSV or just IP)
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) == 1:
                # Just an IP address
                ip_addr = parts[0]
                ip_type = form.default_type.data
                network_type = form.default_network.data
                description = None
            elif len(parts) >= 3:
                # CSV format: ip,type,network[,description]
                ip_addr = parts[0]
                ip_type = parts[1] if parts[1] else form.default_type.data
                network_type = parts[2] if parts[2] else form.default_network.data
                description = parts[3] if len(parts) > 3 else None
            else:
                errors.append(f"Line {line_num}: Invalid format")
                continue
            
            # Validate IP
            is_valid, version, error = validate_ip_address(ip_addr)
            if not is_valid:
                errors.append(f"Line {line_num}: {error}")
                continue
            
            # Check if IP already exists
            if IPAddress.query.filter_by(ip_address=ip_addr).first():
                skipped += 1
                continue
            
            # Create IP
            ip = IPAddress(
                ip_address=ip_addr,
                version=version,
                ip_type=ip_type,
                network_type=network_type,
                status=form.default_status.data,
                datacenter_id=form.datacenter_id.data if form.datacenter_id.data else None,
                description=description
            )
            
            db.session.add(ip)
            imported += 1
        
        db.session.commit()
        
        # Flash results
        flash(f'Import complete: {imported} IPs added, {skipped} skipped', 'success')
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, 'warning')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'warning')
        
        return redirect(url_for('ipam.index'))
    
    return render_template('ipam/bulk_import.html', form=form)

# ========== IP RANGE OPERATIONS ==========

@ipam_bp.route('/ranges')
def ranges():
    """View all IP ranges"""
    ranges = IPRange.query.order_by(IPRange.network_type, IPRange.network).all()
    
    # Calculate stats for each range
    range_stats = []
    for r in ranges:
        # Count IPs in this range (basic check - will improve in Phase 3)
        ip_count = IPAddress.query.filter(
            IPAddress.ip_address.like(f"{r.network.rsplit('.', 1)[0]}.%")
        ).count()
        
        range_stats.append({
            'range': r,
            'ip_count': ip_count
        })
    
    return render_template('ipam/ranges.html', range_stats=range_stats)

@ipam_bp.route('/range/add', methods=['GET', 'POST'])
def add_range():
    """Add a new IP range"""
    form = IPRangeForm()
    
    # Populate datacenter choices
    form.datacenter_id.choices = [(0, '-- No Assignment --')] + [
        (dc.id, f'{dc.code} - {dc.name}') for dc in DataCenter.query.order_by(DataCenter.code).all()
    ]
    
    if form.validate_on_submit():
        # Calculate IP count (simplified for Phase 1)
        total_ips = 2 ** (32 - form.cidr.data)
        usable_ips = total_ips - 2 if total_ips > 2 else total_ips
        
        ip_range = IPRange(
            name=form.name.data,
            network=form.network.data,
            cidr=form.cidr.data,
            gateway=form.gateway.data,
            network_type=form.network_type.data,
            datacenter_id=form.datacenter_id.data if form.datacenter_id.data else None,
            vlan_id=form.vlan_id.data,
            provider=form.provider.data,
            description=form.description.data,
            notes=form.notes.data,
            total_ips=total_ips,
            usable_ips=usable_ips
        )
        
        db.session.add(ip_range)
        db.session.commit()
        
        flash(f'IP range {ip_range.name} ({ip_range.cidr_notation}) added!', 'success')
        return redirect(url_for('ipam.ranges'))
    
    return render_template('ipam/add_range.html', form=form)

@ipam_bp.route('/range/delete/<int:range_id>', methods=['POST'])
def delete_range(range_id):
    """Delete an IP range"""
    ip_range = IPRange.query.get_or_404(range_id)
    
    # Check if any IPs reference this range (future enhancement)
    range_name = ip_range.name
    db.session.delete(ip_range)
    db.session.commit()
    
    flash(f'IP range {range_name} deleted!', 'success')
    return redirect(url_for('ipam.ranges'))

# ========== API ENDPOINTS ==========

@ipam_bp.route('/api/check-ip', methods=['POST'])
def check_ip():
    """API endpoint to check if an IP is available"""
    data = request.get_json()
    ip_address = data.get('ip')
    
    if not ip_address:
        return jsonify({'error': 'No IP provided'}), 400
    
    # Validate IP format
    is_valid, version, error = validate_ip_address(ip_address)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Check if IP exists
    existing = IPAddress.query.filter_by(ip_address=ip_address).first()
    
    if existing:
        return jsonify({
            'available': False,
            'ip': ip_address,
            'status': existing.status,
            'assigned_to': existing.assigned_device_name,
            'type': existing.ip_type
        })
    else:
        return jsonify({
            'available': True,
            'ip': ip_address,
            'message': 'IP is available'
        })

@ipam_bp.route('/api/stats')
def api_stats():
    """Get IPAM statistics"""
    stats = {
        'total_ips': IPAddress.query.count(),
        'assigned': IPAddress.query.filter(IPAddress.assigned_to_type.isnot(None)).count(),
        'available': IPAddress.query.filter_by(status='available').count(),
        'reserved': IPAddress.query.filter_by(status='reserved').count(),
        'ranges': IPRange.query.count(),
        'by_network': {
            'public': IPAddress.query.filter_by(network_type='public').count(),
            'private': IPAddress.query.filter_by(network_type='private').count(),
            'management': IPAddress.query.filter_by(network_type='management').count()
        },
        'by_type': {}
    }
    
    # Count by type
    for ip_type, label in [('management', 'Management'), ('primary', 'Primary'), 
                           ('addon', 'Add-on'), ('virtual', 'Virtual')]:
        stats['by_type'][ip_type] = IPAddress.query.filter_by(ip_type=ip_type).count()
    
    return jsonify(stats)
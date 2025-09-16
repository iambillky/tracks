"""
File: models/ipam.py
Purpose: Simple IP Address Management models for DCMS
Version: 1.0.0
Author: DCMS Team
Date: 2025-01-14

This is Phase 1 of IPAM - just basic IP tracking with no complex subnet math
Future phases will add subnet calculations, IP pools, VLAN mapping, etc.

Revision History:
- v1.0.0: Initial creation with simple IPAddress and IPRange models
         Polymorphic assignment allows IPs to be assigned to any device type
         Basic IP validation and private IP detection
"""

from datetime import datetime
from models.datacenter import db

# ========== IP TYPE CONSTANTS ==========

IP_TYPES = [
    ('management', 'Management IP'),
    ('primary', 'Primary IP'),
    ('addon', 'Add-on IP'),
    ('virtual', 'Virtual IP (VIP)'),
    ('gateway', 'Gateway IP'),
    ('reserved', 'Reserved IP'),
    ('broadcast', 'Broadcast IP'),
    ('network', 'Network IP')
]

IP_STATUS = [
    ('available', 'Available'),
    ('assigned', 'Assigned'),
    ('reserved', 'Reserved'),
    ('deprecated', 'Deprecated'),
    ('conflict', 'Conflict Detected')
]

NETWORK_TYPES = [
    ('public', 'Public Network'),
    ('private', 'Private Network'),
    ('management', 'Management Network'),
    ('dmz', 'DMZ Network')
]

# ========== CORE IPAM MODELS ==========

class IPAddress(db.Model):
    """
    Core IP Address tracking
    Phase 1: Just track IPs and what they're assigned to
    No complex subnet calculations yet - keep it simple
    """
    __tablename__ = 'ip_addresses'
    
    # ========== PRIMARY KEY ==========
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== THE IP ADDRESS ==========
    ip_address = db.Column(db.String(45), unique=True, nullable=False, index=True)  
    # Supports both IPv4 (15 chars max) and IPv6 (45 chars max)
    version = db.Column(db.Integer, default=4)  # 4 or 6
    
    # ========== IP TYPE/PURPOSE ==========
    ip_type = db.Column(db.String(20), nullable=False, default='primary')  
    # Types: 'management', 'primary', 'addon', 'virtual', 'gateway', 'reserved'
    
    # ========== ASSIGNMENT (Polymorphic) ==========
    # This lets us assign IPs to ANY type of device without foreign keys
    assigned_to_type = db.Column(db.String(50))  # 'network_device', 'pdu', 'server', etc.
    assigned_to_id = db.Column(db.Integer)  # ID of the assigned device
    
    # ========== BASIC CATEGORIZATION ==========
    network_type = db.Column(db.String(20), default='private')  # 'public', 'private', 'management'
    vlan_id = db.Column(db.Integer)  # Just store VLAN number for now (future: link to VLAN table)
    
    # ========== LOCATION (Optional) ==========
    datacenter_id = db.Column(db.Integer, db.ForeignKey('datacenters.id'))
    
    # ========== STATUS ==========
    status = db.Column(db.String(20), default='available')  
    # Status: 'available', 'assigned', 'reserved', 'deprecated', 'conflict'
    
    # ========== DNS (Phase 2) ==========
    dns_name = db.Column(db.String(255))  # FQDN if applicable
    reverse_dns = db.Column(db.String(255))  # PTR record
    
    # ========== METADATA ==========
    description = db.Column(db.String(200))
    notes = db.Column(db.Text)
    
    # ========== TIMESTAMPS ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime)  # For future scanning/discovery
    last_ping = db.Column(db.DateTime)  # Last successful ping
    
    # ========== RELATIONSHIPS ==========
    datacenter = db.relationship('DataCenter', backref='ip_addresses')
    
    # ========== PROPERTIES ==========
    @property
    def is_assigned(self):
        """Check if this IP is assigned to a device"""
        return self.assigned_to_type is not None and self.assigned_to_id is not None
    
    @property
    def is_available(self):
        """Check if this IP is available for assignment"""
        return self.status == 'available' and not self.is_assigned
    
    @property
    def is_private(self):
        """Check if this is a private IP (RFC1918)"""
        if self.version == 4:
            parts = self.ip_address.split('.')
            if len(parts) == 4:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    # Check RFC1918 ranges
                    # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
                    return (first == 10 or 
                           (first == 172 and 16 <= second <= 31) or
                           (first == 192 and second == 168))
                except ValueError:
                    return False
        return False
    
    @property
    def assigned_device_name(self):
        """Get the name of the assigned device (helper for display)"""
        if not self.is_assigned:
            return None
        
        # This will be expanded as we add more device types
        if self.assigned_to_type == 'network_device':
            from models.network_device import NetworkDevice
            device = NetworkDevice.query.get(self.assigned_to_id)
            return device.hostname if device else 'Unknown Device'
        elif self.assigned_to_type == 'pdu':
            from models.datacenter import PDU
            pdu = PDU.query.get(self.assigned_to_id)
            return f"PDU {pdu.identifier}" if pdu else 'Unknown PDU'
        # Add more device types as needed
        return f"{self.assigned_to_type} #{self.assigned_to_id}"
    
    def assign_to(self, device_type, device_id):
        """Helper method to assign this IP to a device"""
        self.assigned_to_type = device_type
        self.assigned_to_id = device_id
        self.status = 'assigned'
        self.updated_at = datetime.utcnow()
    
    def release(self):
        """Helper method to release this IP from assignment"""
        self.assigned_to_type = None
        self.assigned_to_id = None
        self.status = 'available'
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        status = f"→ {self.assigned_device_name}" if self.is_assigned else self.status
        return f'<IP {self.ip_address} ({status})>'


class IPRange(db.Model):
    """
    Simple IP Range tracking (for Phase 2)
    Just store our owned ranges, no complex subnet math yet
    This is preparation for future subnet management
    """
    __tablename__ = 'ip_ranges'
    
    # ========== PRIMARY KEY ==========
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== RANGE DEFINITION ==========
    name = db.Column(db.String(100), nullable=False)  # "Public Block 1", "Management Network"
    network = db.Column(db.String(45), nullable=False)  # "208.76.80.0"
    cidr = db.Column(db.Integer, nullable=False)  # 24 for /24
    
    # ========== CALCULATED FIELDS (Phase 2) ==========
    # These will be calculated when we add subnet math
    first_ip = db.Column(db.String(45))  # First usable IP
    last_ip = db.Column(db.String(45))  # Last usable IP
    gateway = db.Column(db.String(45))  # Gateway IP for this range
    broadcast = db.Column(db.String(45))  # Broadcast address
    total_ips = db.Column(db.Integer)  # Total IPs in range
    usable_ips = db.Column(db.Integer)  # Usable IPs (total - network - broadcast)
    
    # ========== CATEGORIZATION ==========
    network_type = db.Column(db.String(20), default='private')  # 'public', 'private'
    datacenter_id = db.Column(db.Integer, db.ForeignKey('datacenters.id'))
    vlan_id = db.Column(db.Integer)  # VLAN assignment
    
    # ========== USAGE TRACKING ==========
    assigned_count = db.Column(db.Integer, default=0)  # How many IPs assigned
    reserved_count = db.Column(db.Integer, default=0)  # How many IPs reserved
    
    # ========== METADATA ==========
    description = db.Column(db.String(200))
    notes = db.Column(db.Text)
    provider = db.Column(db.String(100))  # ISP or provider name
    
    # ========== TIMESTAMPS ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========== RELATIONSHIPS ==========
    datacenter = db.relationship('DataCenter', backref='ip_ranges')
    
    # ========== PROPERTIES ==========
    @property
    def cidr_notation(self):
        """Return the CIDR notation for display"""
        return f"{self.network}/{self.cidr}"
    
    @property
    def utilization_percent(self):
        """Calculate utilization percentage"""
        if self.usable_ips and self.usable_ips > 0:
            used = self.assigned_count + self.reserved_count
            return round((used / self.usable_ips) * 100, 1)
        return 0
    
    @property
    def available_count(self):
        """Calculate available IPs"""
        if self.usable_ips:
            return self.usable_ips - self.assigned_count - self.reserved_count
        return 0
    
    def __repr__(self):
        return f'<IPRange {self.name} ({self.cidr_notation})>'


# ========== HELPER FUNCTIONS ==========

def find_duplicate_ips():
    """
    Find any duplicate IP assignments across all tables
    This is a safety check for data integrity
    """
    duplicates = []
    
    # Check for IPs assigned to multiple devices
    assigned_ips = IPAddress.query.filter(
        IPAddress.assigned_to_type.isnot(None)
    ).all()
    
    # Group by device assignment
    assignments = {}
    for ip in assigned_ips:
        key = f"{ip.assigned_to_type}:{ip.assigned_to_id}"
        if ip.ip_address in assignments:
            duplicates.append({
                'ip': ip.ip_address,
                'assignments': [assignments[ip.ip_address], key]
            })
        else:
            assignments[ip.ip_address] = key
    
    return duplicates


def get_next_available_ip(network_type='private', datacenter_id=None):
    """
    Get the next available IP from a pool
    Phase 1: Just return None - this is a placeholder
    Phase 2: Will implement actual IP allocation logic
    """
    # TODO: Implement in Phase 2 with subnet calculations
    return None


def validate_ip_address(ip_string):
    """
    Basic IP address validation
    Returns (is_valid, version, error_message)
    """
    if not ip_string:
        return False, None, "IP address cannot be empty"
    
    # Check for IPv4
    parts = ip_string.split('.')
    if len(parts) == 4:
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False, None, f"Invalid octet: {part}"
            return True, 4, None
        except ValueError:
            return False, None, "Invalid IPv4 format"
    
    # Basic IPv6 check (simplified)
    if ':' in ip_string:
        # Very basic IPv6 validation
        # TODO: Add proper IPv6 validation in Phase 2
        return True, 6, None
    
    return False, None, "Invalid IP address format"
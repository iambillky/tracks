"""
File: models/vlan.py
Purpose: VLAN and VLANSubnet models for Phase 1 IPAM
Version: 1.0.0
Author: DCMS Team
Date: 2025-01-16

Phase 1 Implementation:
- Track VLANs with their purpose (infrastructure vs colocation)
- Support multiple subnets per VLAN (primary + secondaries)
- Map VLANs to IP ranges

Revision History:
- v1.0.0: Initial creation for Phase 1 IPAM Foundation
"""

from datetime import datetime
from models.datacenter import db

# ========== VLAN CONSTANTS ==========

VLAN_PURPOSES = [
    ('infrastructure', 'Infrastructure'),
    ('colocation', 'Colocation'), 
    ('management', 'Management'),
    ('private', 'Private Network'),
    ('transit', 'Transit/Uplink')
]

VLAN_STATUS = [
    ('active', 'Active'),
    ('deprecated', 'Deprecated'),
    ('reserved', 'Reserved')
]

# ========== VLAN MODEL ==========

class VLAN(db.Model):
    """
    VLAN tracking for Phase 1
    Core model to track VLANs and their purpose
    """
    __tablename__ = 'vlans'
    
    # ========== PRIMARY KEY ==========
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== VLAN IDENTIFICATION ==========
    vlan_id = db.Column(db.Integer, unique=True, nullable=False, index=True)  # The actual VLAN number (1-4094)
    name = db.Column(db.String(100), nullable=False)  # "Vlan2", "Vlan201", etc from router
    description = db.Column(db.String(255))  # Detailed description from router config
    
    # ========== VLAN PURPOSE ==========
    purpose = db.Column(db.String(20), nullable=False, default='infrastructure')
    # 'infrastructure' - Internal use (208.76.x.x, 199.58.x.x)
    # 'colocation' - Customer use (66.51.159.x)
    # 'management' - Management network (10.x.x.x)
    # 'private' - Private network
    # 'transit' - Uplink/transit
    
    # ========== STATUS ==========
    status = db.Column(db.String(20), default='active')
    
    # ========== LOCATION ==========
    datacenter_id = db.Column(db.Integer, db.ForeignKey('datacenters.id'))
    
    # ========== METADATA ==========
    notes = db.Column(db.Text)
    
    # ========== TIMESTAMPS ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========== RELATIONSHIPS ==========
    datacenter = db.relationship('DataCenter', backref='vlans')
    subnets = db.relationship('VLANSubnet', back_populates='vlan', cascade='all, delete-orphan')
    
    # ========== PROPERTIES ==========
    @property
    def primary_subnet(self):
        """Get the primary subnet for this VLAN"""
        for subnet in self.subnets:
            if subnet.is_primary:
                return subnet
        return None
    
    @property
    def secondary_subnets(self):
        """Get all secondary subnets for this VLAN"""
        return [s for s in self.subnets if not s.is_primary]
    
    @property
    def total_ip_count(self):
        """Calculate total IPs across all subnets"""
        total = 0
        for subnet in self.subnets:
            total += subnet.total_ips
        return total
    
    @property
    def subnet_count(self):
        """Count of subnets (primary + secondaries)"""
        return len(self.subnets)
    
    def __repr__(self):
        return f'<VLAN {self.vlan_id}: {self.name} ({self.purpose})>'


# ========== VLAN SUBNET MODEL ==========

class VLANSubnet(db.Model):
    """
    Subnet assignments for VLANs
    Tracks primary and secondary subnets per VLAN
    """
    __tablename__ = 'vlan_subnets'
    
    # ========== PRIMARY KEY ==========
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== VLAN REFERENCE ==========
    vlan_id = db.Column(db.Integer, db.ForeignKey('vlans.id'), nullable=False)
    
    # ========== SUBNET DEFINITION ==========
    subnet = db.Column(db.String(45), nullable=False)  # "208.76.80.0/25"
    gateway = db.Column(db.String(45), nullable=False)  # "208.76.80.254" or "208.76.80.1"
    
    # ========== PRIMARY/SECONDARY ==========
    is_primary = db.Column(db.Boolean, default=True)  # True for primary, False for secondary
    
    # ========== NETWORK INFO ==========
    network_address = db.Column(db.String(45))  # "208.76.80.0"
    broadcast_address = db.Column(db.String(45))  # "208.76.80.127"
    cidr = db.Column(db.Integer)  # 25
    total_ips = db.Column(db.Integer)  # 128
    usable_ips = db.Column(db.Integer)  # 126
    
    # ========== USAGE TRACKING ==========
    assigned_count = db.Column(db.Integer, default=0)
    reserved_count = db.Column(db.Integer, default=0)
    
    # ========== METADATA ==========
    notes = db.Column(db.Text)
    
    # ========== TIMESTAMPS ==========
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========== RELATIONSHIPS ==========
    vlan = db.relationship('VLAN', back_populates='subnets')
    
    # ========== PROPERTIES ==========
    @property
    def available_count(self):
        """Calculate available IPs"""
        if self.usable_ips:
            return self.usable_ips - self.assigned_count - self.reserved_count
        return 0
    
    @property
    def utilization_percent(self):
        """Calculate utilization percentage"""
        if self.usable_ips and self.usable_ips > 0:
            used = self.assigned_count + self.reserved_count
            return round((used / self.usable_ips) * 100, 1)
        return 0
    
    @property
    def subnet_type(self):
        """Determine subnet type based on gateway IP"""
        if self.subnet.startswith('66.51.159'):
            return 'colocation'
        elif self.subnet.startswith('10.'):
            return 'private'
        elif self.subnet.startswith('208.76') or self.subnet.startswith('199.58'):
            return 'infrastructure'
        else:
            return 'unknown'
    
    def __repr__(self):
        primary = "Primary" if self.is_primary else "Secondary"
        return f'<VLANSubnet {self.subnet} ({primary}) for VLAN {self.vlan_id}>'


# ========== HELPER FUNCTIONS ==========

def calculate_subnet_info(subnet_cidr):
    """
    Calculate subnet information from CIDR notation
    
    Args:
        subnet_cidr: String like "208.76.80.0/25"
    
    Returns:
        dict with network_address, broadcast_address, total_ips, usable_ips
    """
    try:
        import ipaddress
        network = ipaddress.IPv4Network(subnet_cidr, strict=False)
        
        return {
            'network_address': str(network.network_address),
            'broadcast_address': str(network.broadcast_address),
            'cidr': network.prefixlen,
            'total_ips': network.num_addresses,
            'usable_ips': network.num_addresses - 2 if network.num_addresses > 2 else network.num_addresses
        }
    except:
        # Fallback for simple calculation
        parts = subnet_cidr.split('/')
        if len(parts) == 2:
            cidr = int(parts[1])
            total = 2 ** (32 - cidr)
            return {
                'network_address': parts[0],
                'broadcast_address': None,
                'cidr': cidr,
                'total_ips': total,
                'usable_ips': total - 2 if total > 2 else total
            }
    
    return {
        'network_address': subnet_cidr.split('/')[0] if '/' in subnet_cidr else subnet_cidr,
        'broadcast_address': None,
        'cidr': None,
        'total_ips': 0,
        'usable_ips': 0
    }
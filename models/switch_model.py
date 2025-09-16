"""
File: models/switch_model.py
Purpose: Switch equipment library - defines specific switch models and their specifications
Version: 1.0.0
Author: DCMS Team
Created: 2025-01-14

This model stores the specifications for your 6 standard switch models:
- MikroTik: CRS326-24S+2Q+, CRS354-48G-4S+2Q+, CSS326-24G-2S+
- Arista: DCS-7048T-A, DCS-7124SX, DCS-7050S-52

When a user selects a model, the system automatically:
- Sets the correct port count
- Creates all ports with proper naming
- Sets power consumption
- Configures default port speeds
"""

from datetime import datetime
from models.datacenter import db

# ========== SWITCH MODEL ==========

class SwitchModel(db.Model):
    """
    Equipment library for network switches
    Stores specifications for specific switch models used in the data center
    """
    __tablename__ = 'switch_models'
    
    # ========== PRIMARY KEY ==========
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== MODEL IDENTIFICATION ==========
    manufacturer = db.Column(db.String(50), nullable=False)  # MikroTik, Arista
    model_number = db.Column(db.String(100), nullable=False, unique=True)  # CRS354-48G-4S+2Q+
    display_name = db.Column(db.String(200), nullable=False)  # User-friendly display name
    
    # ========== PORT CONFIGURATION ==========
    copper_1g_ports = db.Column(db.Integer, default=0)  # Number of 1G copper ports
    copper_10g_ports = db.Column(db.Integer, default=0)  # Number of 10G copper ports (rare)
    sfp_ports = db.Column(db.Integer, default=0)  # Number of SFP ports (1G fiber)
    sfp_plus_ports = db.Column(db.Integer, default=0)  # Number of SFP+ ports (10G fiber)
    qsfp_ports = db.Column(db.Integer, default=0)  # Number of QSFP+ ports (40G)
    qsfp28_ports = db.Column(db.Integer, default=0)  # Number of QSFP28 ports (100G)
    
    total_ports = db.Column(db.Integer, nullable=False)  # Total port count
    
    # ========== PORT NAMING SCHEME ==========
    port_naming_scheme = db.Column(db.String(50), nullable=False)  # mikrotik_ros, mikrotik_swos, arista
    
    # ========== PHYSICAL SPECIFICATIONS ==========
    rack_units = db.Column(db.Integer, default=1)  # Size in rack units
    power_consumption_idle = db.Column(db.Integer)  # Watts at idle
    power_consumption_typical = db.Column(db.Integer)  # Watts typical usage
    power_consumption_max = db.Column(db.Integer)  # Watts maximum
    
    # ========== CAPABILITIES ==========
    max_vlans = db.Column(db.Integer, default=4094)  # Maximum VLANs supported
    switching_capacity_gbps = db.Column(db.Integer)  # Backplane capacity
    forwarding_rate_mpps = db.Column(db.Integer)  # Million packets per second
    
    # ========== LIFECYCLE ==========
    is_legacy = db.Column(db.Boolean, default=False)  # True for MikroTik (being phased out)
    is_current = db.Column(db.Boolean, default=True)  # Currently in use
    eol_date = db.Column(db.Date)  # End of life date if known
    
    # ========== METADATA ==========
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ========== RELATIONSHIPS ==========
    # This will link to network devices that use this model
    devices = db.relationship('NetworkDevice', backref='switch_model', lazy='dynamic')
    
    def __repr__(self):
        return f'<SwitchModel {self.manufacturer} {self.model_number}>'
    
    # ========== METHODS ==========
    
    def get_port_configuration(self):
        """
        Returns a dictionary describing the port configuration
        Used by the port creation logic
        """
        config = {
            'total': self.total_ports,
            'scheme': self.port_naming_scheme,
            'ports': []
        }
        
        port_num = 1
        
        # Add copper 1G ports
        for i in range(1, self.copper_1g_ports + 1):
            config['ports'].append({
                'number': port_num,
                'type': 'copper',
                'speed': 1000,
                'name': self._generate_port_name(port_num, 'copper')
            })
            port_num += 1
        
        # Add SFP ports (1G fiber)
        for i in range(1, self.sfp_ports + 1):
            config['ports'].append({
                'number': port_num,
                'type': 'sfp',
                'speed': 1000,
                'name': self._generate_port_name(port_num, 'sfp')
            })
            port_num += 1
        
        # Add SFP+ ports (10G fiber)
        sfp_plus_start = port_num
        for i in range(1, self.sfp_plus_ports + 1):
            config['ports'].append({
                'number': port_num,
                'type': 'sfp_plus',
                'speed': 10000,
                'name': self._generate_port_name(port_num, 'sfp_plus', i, sfp_plus_start)
            })
            port_num += 1
        
        # Add QSFP+ ports (40G)
        qsfp_start = port_num
        for i in range(1, self.qsfp_ports + 1):
            config['ports'].append({
                'number': port_num,
                'type': 'qsfp',
                'speed': 40000,
                'name': self._generate_port_name(port_num, 'qsfp', i, qsfp_start)
            })
            port_num += 1
        
        return config
    
    def _generate_port_name(self, port_num, port_type, index=None, start_num=None):
        """
        Generate port name based on manufacturer naming scheme
        """
        if self.port_naming_scheme == 'mikrotik_ros':
            # MikroTik RouterOS naming
            if port_type == 'copper':
                return f'ether{port_num}'
            elif port_type in ['sfp', 'sfp_plus']:
                # SFP+ ports are numbered separately
                if index and start_num:
                    return f'sfp-sfpplus{index}'
                return f'sfp{port_num}'
            elif port_type == 'qsfp':
                if index:
                    return f'qsfpplus{index}'
                return f'qsfpplus{port_num}'
        
        elif self.port_naming_scheme == 'mikrotik_swos':
            # MikroTik SwOS naming (simpler)
            if port_type in ['copper', 'sfp']:
                return f'port{port_num}'
            elif port_type == 'sfp_plus':
                if index and start_num:
                    return f'sfp-sfpplus{index}'
                return f'sfp{port_num}'
        
        elif self.port_naming_scheme == 'arista':
            # Arista naming - all ports are "Ethernet"
            return f'Ethernet{port_num}'
        
        # Default fallback
        return f'Port{port_num}'


# ========== DEFAULT SWITCH MODELS ==========

def get_default_switch_models():
    """
    Returns the 6 standard switch models for this data center
    """
    return [
        {
            'manufacturer': 'MikroTik',
            'model_number': 'CRS326-24S+2Q+',
            'display_name': 'MikroTik CRS326-24S+2Q+ (24x SFP+, 2x QSFP+)',
            'copper_1g_ports': 0,
            'sfp_plus_ports': 24,
            'qsfp_ports': 2,
            'total_ports': 26,
            'port_naming_scheme': 'mikrotik_ros',
            'rack_units': 1,
            'power_consumption_typical': 50,
            'power_consumption_max': 80,
            'is_legacy': True,  # Being phased out
            'notes': '24-port 10G SFP+ switch with 2x 40G QSFP+ uplinks. Private network.'
        },
        {
            'manufacturer': 'MikroTik',
            'model_number': 'CRS354-48G-4S+2Q+',
            'display_name': 'MikroTik CRS354-48G-4S+2Q+ (48x 1G, 4x 10G, 2x 40G)',
            'copper_1g_ports': 48,
            'sfp_plus_ports': 4,
            'qsfp_ports': 2,
            'total_ports': 54,
            'port_naming_scheme': 'mikrotik_ros',
            'rack_units': 1,
            'power_consumption_typical': 60,
            'power_consumption_max': 90,
            'is_legacy': True,  # Being phased out
            'notes': '48-port Gigabit with 4x SFP+ and 2x QSFP+ uplinks. Private network access switch.'
        },
        {
            'manufacturer': 'MikroTik',
            'model_number': 'CSS326-24G-2S+',
            'display_name': 'MikroTik CSS326-24G-2S+ (24x 1G, 2x 10G)',
            'copper_1g_ports': 24,
            'sfp_plus_ports': 2,
            'qsfp_ports': 0,
            'total_ports': 26,
            'port_naming_scheme': 'mikrotik_swos',  # Uses SwOS, not RouterOS
            'rack_units': 1,
            'power_consumption_typical': 35,
            'power_consumption_max': 50,
            'is_legacy': True,  # Being phased out
            'notes': '24-port Gigabit with 2x SFP+ uplinks. SwOS-based switch.'
        },
        {
            'manufacturer': 'Arista',
            'model_number': 'DCS-7048T-A',
            'display_name': 'Arista 7048T-A (48x 1G Copper, 4x 10G SFP+)',
            'copper_1g_ports': 48,
            'sfp_plus_ports': 4,
            'qsfp_ports': 0,
            'total_ports': 52,
            'port_naming_scheme': 'arista',
            'rack_units': 1,
            'power_consumption_typical': 125,
            'power_consumption_max': 200,
            'is_legacy': False,
            'notes': '48-port Gigabit copper with 4x SFP+ uplinks. Standard access switch.'
        },
        {
            'manufacturer': 'Arista',
            'model_number': 'DCS-7124SX',
            'display_name': 'Arista 7124SX (24x 10G SFP+)',
            'copper_1g_ports': 0,
            'sfp_plus_ports': 24,
            'qsfp_ports': 0,
            'total_ports': 24,
            'port_naming_scheme': 'arista',
            'rack_units': 1,
            'power_consumption_typical': 175,
            'power_consumption_max': 250,
            'is_legacy': False,
            'notes': '24-port 10G SFP+ switch. High-performance, low latency.'
        },
        {
            'manufacturer': 'Arista',
            'model_number': 'DCS-7050S-52',
            'display_name': 'Arista 7050S-52 (52x 10G SFP+)',
            'copper_1g_ports': 0,
            'sfp_plus_ports': 52,
            'qsfp_ports': 0,
            'total_ports': 52,
            'port_naming_scheme': 'arista',
            'rack_units': 1,
            'power_consumption_typical': 210,
            'power_consumption_max': 300,
            'is_legacy': False,
            'notes': '52-port 10G SFP+ switch. Last 4 ports often used as 40G with QSFP adapters.'
        }
    ]


def init_default_switch_models(session):
    """
    Initialize the database with default switch models
    Called during app initialization if no models exist
    """
    from models.switch_model import SwitchModel
    
    models = get_default_switch_models()
    for model_data in models:
        model = SwitchModel(**model_data)
        session.add(model)
    
    session.commit()
    print(f"Initialized {len(models)} switch models in equipment library")
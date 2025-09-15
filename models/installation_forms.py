"""
File: forms/installation_forms.py
Purpose: Unified installation forms that capture complete device setup
Version: 1.0.0
Author: DCMS Team
Created: 2025-01-14

These forms capture EVERYTHING needed when a tech installs a device:
- Network connectivity (switch/port)
- Power connectivity (PDU/outlet)
- IP assignment with VLAN
- Physical location
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, TextAreaField, SelectField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, IPAddress, ValidationError
from models.network_device import NetworkDevice
from models.datacenter import PDU

# ========== CUSTOM VALIDATORS ==========

def validate_unique_hostname(form, field):
    """Validate hostname is unique"""
    if field.data:
        existing = NetworkDevice.query.filter_by(hostname=field.data.upper()).first()
        if existing:
            raise ValidationError(f'Hostname {field.data.upper()} already exists')

def validate_ip_available(form, field):
    """Validate IP is available in IPAM"""
    if field.data:
        from models.ipam import IPAddress
        existing = IPAddress.query.filter_by(ip_address=field.data).first()
        if existing:
            raise ValidationError(f'IP {field.data} is already assigned to {existing.assigned_device_name}')

# ========== NETWORK DEVICE INSTALLATION FORM ==========

class NetworkDeviceInstallationForm(FlaskForm):
    """
    Complete installation form for network devices (switches, routers, etc.)
    Captures all connectivity and configuration in one place
    """
    
    # ========== DEVICE IDENTIFICATION ==========
    hostname = StringField('Hostname', 
                          validators=[DataRequired(), Length(max=100), validate_unique_hostname],
                          render_kw={'placeholder': 'TCH-SFJ-INT5', 
                                   'style': 'text-transform: uppercase;'})
    
    identifier = StringField('Identifier', 
                           validators=[DataRequired(), Length(max=50)],
                           render_kw={'placeholder': 'INT5, DISTRO1, CORE',
                                    'style': 'text-transform: uppercase;'})
    
    device_type = SelectField('Device Type',
                            choices=[
                                ('Switch', 'Switch'),
                                ('Core', 'Core Switch/Router'),
                                ('Firewall', 'Firewall'),
                                ('Load Balancer', 'Load Balancer')
                            ],
                            validators=[DataRequired()])
    
    # ========== PHYSICAL LOCATION ==========
    rack_id = SelectField('Rack Location', coerce=int, validators=[DataRequired()])
    start_u = IntegerField('Starting U Position', 
                          validators=[DataRequired(), NumberRange(min=1, max=50)])
    size_u = IntegerField('Size (in U)', 
                         validators=[DataRequired(), NumberRange(min=1, max=10)],
                         default=1)
    
    # ========== NETWORK CONNECTIVITY (IP + VLAN) ==========
    management_ip = StringField('Management IP Address',
                               validators=[DataRequired(), IPAddress(), validate_ip_available],
                               render_kw={'placeholder': '10.10.5.100'})
    
    vlan_id = IntegerField('VLAN ID',
                          validators=[DataRequired(), NumberRange(min=1, max=4094)],
                          render_kw={'placeholder': 'Management VLAN'})
    
    # ========== UPLINK CONNECTIONS (up to 4) ==========
    # Uplink 1
    uplink_1_switch_id = SelectField('Uplink 1 - Switch', coerce=int, validators=[Optional()])
    uplink_1_port = IntegerField('Uplink 1 - Port', 
                                validators=[Optional(), NumberRange(min=1, max=52)])
    
    # Uplink 2
    uplink_2_switch_id = SelectField('Uplink 2 - Switch (LAG)', coerce=int, validators=[Optional()])
    uplink_2_port = IntegerField('Uplink 2 - Port', 
                                validators=[Optional(), NumberRange(min=1, max=52)])
    
    # Uplink 3
    uplink_3_switch_id = SelectField('Uplink 3 - Switch (LAG)', coerce=int, validators=[Optional()])
    uplink_3_port = IntegerField('Uplink 3 - Port', 
                                validators=[Optional(), NumberRange(min=1, max=52)])
    
    # Uplink 4
    uplink_4_switch_id = SelectField('Uplink 4 - Switch (LAG)', coerce=int, validators=[Optional()])
    uplink_4_port = IntegerField('Uplink 4 - Port', 
                                validators=[Optional(), NumberRange(min=1, max=52)])
    
    # LAG Configuration
    lag_enabled = BooleanField('Enable LAG/Port-Channel')
    port_channel_number = IntegerField('Port-Channel Number',
                                      validators=[Optional(), NumberRange(min=1, max=4096)])
    
    # ========== POWER CONNECTIVITY ==========
    pdu_1_id = SelectField('Primary PDU', coerce=int, validators=[DataRequired()])
    pdu_1_outlet = IntegerField('Primary PDU Outlet', 
                               validators=[DataRequired(), NumberRange(min=1, max=48)])
    
    pdu_2_id = SelectField('Redundant PDU', coerce=int, validators=[Optional()])
    pdu_2_outlet = IntegerField('Redundant PDU Outlet', 
                               validators=[Optional(), NumberRange(min=1, max=48)])
    
    power_consumption = FloatField('Power Consumption (Watts)', 
                                  validators=[Optional(), NumberRange(min=0)])
    
    # ========== HARDWARE INFO ==========
    manufacturer = StringField('Manufacturer', validators=[Optional()])
    model = StringField('Model', validators=[Optional()])
    serial_number = StringField('Serial Number', validators=[Optional()])
    port_count = IntegerField('Total Port Count', validators=[Optional()])
    
    # ========== NOTES ==========
    notes = TextAreaField('Installation Notes', validators=[Optional()])
    
    def validate(self, **kwargs):
        """Custom validation"""
        if not super().validate(**kwargs):
            return False
        
        # If LAG is enabled, need at least 2 uplinks
        if self.lag_enabled.data:
            uplink_count = sum([
                1 if self.uplink_1_switch_id.data else 0,
                1 if self.uplink_2_switch_id.data else 0,
                1 if self.uplink_3_switch_id.data else 0,
                1 if self.uplink_4_switch_id.data else 0
            ])
            if uplink_count < 2:
                self.lag_enabled.errors.append('LAG requires at least 2 uplinks')
                return False
            if not self.port_channel_number.data:
                self.port_channel_number.errors.append('Port-Channel number required when LAG enabled')
                return False
        
        # Validate PDU redundancy
        if self.pdu_2_id.data and self.pdu_1_id.data == self.pdu_2_id.data:
            self.pdu_2_id.errors.append('Redundant PDU must be different from primary')
            return False
        
        return True


# ========== PDU INSTALLATION FORM ==========

class PDUInstallationForm(FlaskForm):
    """
    Complete installation form for PDUs
    Captures power, network, and management configuration
    """
    
    # ========== PDU IDENTIFICATION ==========
    identifier = StringField('PDU Identifier', 
                           validators=[DataRequired(), Length(max=50)],
                           render_kw={'placeholder': 'APC 1'})
    
    model = StringField('Model Number', 
                       validators=[Optional(), Length(max=50)],
                       render_kw={'placeholder': 'AP7932'})
    
    # ========== PHYSICAL LOCATION ==========
    rack_id = SelectField('Rack Location', coerce=int, validators=[DataRequired()])
    
    # ========== ELECTRICAL ==========
    circuit_id = StringField('Circuit ID', validators=[Optional()])
    capacity_amps = FloatField('Capacity (Amps)', 
                             validators=[DataRequired(), NumberRange(min=0, max=100)])
    voltage = SelectField('Voltage', 
                         choices=[(120, '120V'), (208, '208V'), (240, '240V')],
                         coerce=int, validators=[DataRequired()])
    total_outlets = IntegerField('Total Outlets', 
                                validators=[DataRequired(), NumberRange(min=1, max=48)])
    
    # ========== NETWORK CONNECTIVITY ==========
    management_ip = StringField('Management IP Address',
                               validators=[Optional(), IPAddress(), validate_ip_available],
                               render_kw={'placeholder': '10.10.4.100'})
    
    vlan_id = IntegerField('VLAN ID',
                          validators=[Optional(), NumberRange(min=1, max=4094)],
                          render_kw={'placeholder': 'Management VLAN'})
    
    management_switch_id = SelectField('Management Switch', coerce=int, validators=[Optional()])
    management_switch_port = IntegerField('Switch Port', 
                                         validators=[Optional(), NumberRange(min=1, max=52)])
    
    # ========== NOTES ==========
    notes = TextAreaField('Installation Notes', validators=[Optional()])
    
    def validate(self, **kwargs):
        """Custom validation"""
        if not super().validate(**kwargs):
            return False
        
        # If management IP provided, need switch and port
        if self.management_ip.data:
            if not self.management_switch_id.data:
                self.management_switch_id.errors.append('Switch required when management IP configured')
                return False
            if not self.management_switch_port.data:
                self.management_switch_port.errors.append('Port required when management IP configured')
                return False
        
        return True
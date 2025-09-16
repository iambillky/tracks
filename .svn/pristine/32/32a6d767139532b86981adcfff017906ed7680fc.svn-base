"""
File: forms/ipam_forms.py
Purpose: WTForms form definitions for IP Address Management
Version: 1.0.0
Author: DCMS Team
Created: 2025-01-14

Revision History:
- v1.0.0: Initial creation with IPAddress and IPRange forms
         Basic validation for IP format and duplicates
         Support for quick add and bulk import
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, IPAddress, ValidationError
from models.ipam import IPAddress as IPAddressModel, IP_TYPES, IP_STATUS, NETWORK_TYPES

# ========== CUSTOM VALIDATORS ==========

def validate_unique_ip(form, field):
    """Validate that IP address is unique"""
    if field.data:
        # Check if we're editing (form has an ip_id field)
        existing = IPAddressModel.query.filter_by(ip_address=field.data).first()
        
        # If editing, allow the same IP for this record
        if hasattr(form, 'ip_id') and form.ip_id.data:
            if existing and existing.id != int(form.ip_id.data):
                raise ValidationError(f'IP address {field.data} already exists in IPAM')
        else:
            # New IP - must not exist
            if existing:
                raise ValidationError(f'IP address {field.data} already exists in IPAM')

def validate_cidr(form, field):
    """Validate CIDR notation (1-32 for IPv4, 1-128 for IPv6)"""
    if field.data:
        if field.data < 1 or field.data > 32:  # IPv4 for now
            raise ValidationError('CIDR must be between 1 and 32 for IPv4')

# ========== FORM DEFINITIONS ==========

class IPAddressForm(FlaskForm):
    """
    Form for adding/editing individual IP addresses
    Supports manual entry and device assignment
    """
    # ========== HIDDEN FIELD FOR EDITING ==========
    ip_id = HiddenField('IP ID')
    
    # ========== IP ADDRESS ==========
    ip_address = StringField('IP Address',
                            validators=[
                                DataRequired(),
                                IPAddress(ipv4=True, ipv6=False, message='Invalid IPv4 address'),
                                validate_unique_ip
                            ],
                            render_kw={'placeholder': '10.10.5.100', 'class': 'mono'})
    
    # ========== IP TYPE ==========
    ip_type = SelectField('IP Type',
                         choices=[('', '-- Select Type --')] + IP_TYPES,
                         validators=[DataRequired()],
                         default='primary')
    
    # ========== NETWORK CLASSIFICATION ==========
    network_type = SelectField('Network Type',
                              choices=[('', '-- Select Network --')] + NETWORK_TYPES,
                              validators=[DataRequired()],
                              default='private')
    
    # ========== VLAN ==========
    vlan_id = IntegerField('VLAN ID',
                          validators=[Optional()],
                          render_kw={'placeholder': 'Optional VLAN number'})
    
    # ========== STATUS ==========
    status = SelectField('Status',
                        choices=IP_STATUS,
                        validators=[DataRequired()],
                        default='available')
    
    # ========== LOCATION ==========
    datacenter_id = SelectField('Data Center',
                               coerce=int,
                               validators=[Optional()])
    
    # ========== DNS ==========
    dns_name = StringField('DNS Name (FQDN)',
                          validators=[Optional(), Length(max=255)],
                          render_kw={'placeholder': 'server1.example.com'})
    
    # ========== METADATA ==========
    description = StringField('Description',
                            validators=[Optional(), Length(max=200)],
                            render_kw={'placeholder': 'Brief description of IP usage'})
    
    notes = TextAreaField('Notes',
                         validators=[Optional()],
                         render_kw={'rows': 3, 'placeholder': 'Additional notes or comments'})


class QuickIPAddForm(FlaskForm):
    """
    Simplified form for quickly adding IPs
    Used in modal dialogs and quick-add scenarios
    """
    ip_address = StringField('IP Address',
                            validators=[
                                DataRequired(),
                                IPAddress(ipv4=True, ipv6=False),
                                validate_unique_ip
                            ],
                            render_kw={'placeholder': '10.10.5.100', 'class': 'mono'})
    
    ip_type = SelectField('Type',
                         choices=IP_TYPES,
                         default='primary')
    
    network_type = SelectField('Network',
                              choices=NETWORK_TYPES,
                              default='private')
    
    description = StringField('Quick Note',
                            validators=[Optional(), Length(max=200)],
                            render_kw={'placeholder': 'What is this IP for?'})


class BulkIPImportForm(FlaskForm):
    """
    Form for bulk importing IP addresses
    Supports CSV format and range notation
    """
    import_data = TextAreaField('IP Addresses',
                               validators=[DataRequired()],
                               render_kw={
                                   'rows': 10,
                                   'placeholder': 'Enter IPs (one per line) or paste CSV:\n'
                                                '10.10.5.100\n'
                                                '10.10.5.101\n'
                                                '192.168.1.50,management,private,Switch management\n'
                                                '208.76.80.10,primary,public,Web server'
                               })
    
    default_type = SelectField('Default IP Type',
                              choices=IP_TYPES,
                              default='primary',
                              description='Type to use if not specified in CSV')
    
    default_network = SelectField('Default Network',
                                 choices=NETWORK_TYPES,
                                 default='private',
                                 description='Network type if not specified')
    
    default_status = SelectField('Default Status',
                                choices=IP_STATUS,
                                default='available')
    
    datacenter_id = SelectField('Assign to Data Center',
                               coerce=int,
                               validators=[Optional()])


class IPRangeForm(FlaskForm):
    """
    Form for defining IP ranges/subnets
    Phase 2: Just store ranges, no complex calculations yet
    """
    # ========== RANGE IDENTIFICATION ==========
    name = StringField('Range Name',
                      validators=[DataRequired(), Length(max=100)],
                      render_kw={'placeholder': 'Public Block 1, Management Network, etc.'})
    
    # ========== NETWORK DEFINITION ==========
    network = StringField('Network Address',
                         validators=[
                             DataRequired(),
                             IPAddress(ipv4=True, ipv6=False, message='Invalid network address')
                         ],
                         render_kw={'placeholder': '10.10.0.0', 'class': 'mono'})
    
    cidr = IntegerField('CIDR Prefix',
                       validators=[DataRequired(), validate_cidr],
                       render_kw={'placeholder': '24'})
    
    # ========== GATEWAY ==========
    gateway = StringField('Gateway IP',
                         validators=[
                             Optional(),
                             IPAddress(ipv4=True, ipv6=False)
                         ],
                         render_kw={'placeholder': '10.10.0.1', 'class': 'mono'})
    
    # ========== CLASSIFICATION ==========
    network_type = SelectField('Network Type',
                              choices=NETWORK_TYPES,
                              validators=[DataRequired()],
                              default='private')
    
    datacenter_id = SelectField('Data Center',
                               coerce=int,
                               validators=[Optional()])
    
    vlan_id = IntegerField('VLAN ID',
                          validators=[Optional()],
                          render_kw={'placeholder': 'Associated VLAN'})
    
    # ========== METADATA ==========
    provider = StringField('Provider/ISP',
                          validators=[Optional(), Length(max=100)],
                          render_kw={'placeholder': 'ISP or provider name'})
    
    description = StringField('Description',
                            validators=[Optional(), Length(max=200)],
                            render_kw={'placeholder': 'Purpose of this IP range'})
    
    notes = TextAreaField('Notes',
                         validators=[Optional()],
                         render_kw={'rows': 3})


class IPSearchForm(FlaskForm):
    """
    Form for searching/filtering IP addresses
    Used in the main IPAM view
    """
    search = StringField('Search',
                        validators=[Optional()],
                        render_kw={'placeholder': 'IP, hostname, or description...'})
    
    network_type = SelectField('Network',
                              choices=[('all', 'All Networks')] + NETWORK_TYPES,
                              default='all')
    
    ip_type = SelectField('Type',
                         choices=[('all', 'All Types')] + IP_TYPES,
                         default='all')
    
    status = SelectField('Status',
                        choices=[('all', 'All Status')] + IP_STATUS,
                        default='all')
    
    datacenter_id = SelectField('Data Center',
                               choices=[('all', 'All DCs')],
                               default='all')
    
    assignment = SelectField('Assignment',
                           choices=[
                               ('all', 'All IPs'),
                               ('assigned', 'Assigned Only'),
                               ('unassigned', 'Unassigned Only')
                           ],
                           default='all')
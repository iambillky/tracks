"""
File: forms/vlan_forms.py
Purpose: WTForms for VLAN management in Phase 1 IPAM
Version: 1.0.0
Author: DCMS Team
Date: 2025-01-16

Forms for:
- Creating/editing VLANs
- Adding subnets to VLANs
- Importing router configurations
- Importing ARIN allocations

Revision History:
- v1.0.0: Initial creation for Phase 1 IPAM Foundation
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, BooleanField, FileField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError, IPAddress
from models.vlan import VLAN, VLAN_PURPOSES, VLAN_STATUS

# ========== CUSTOM VALIDATORS ==========

def validate_vlan_id(form, field):
    """Validate VLAN ID is in valid range and unique"""
    if field.data:
        # Check valid range
        if field.data < 1 or field.data > 4094:
            raise ValidationError('VLAN ID must be between 1 and 4094')
        
        # Check if unique (only for new VLANs)
        if not hasattr(form, 'original_vlan_id'):
            existing = VLAN.query.filter_by(vlan_id=field.data).first()
            if existing:
                raise ValidationError(f'VLAN {field.data} already exists')

def validate_subnet_cidr(form, field):
    """Validate subnet is in CIDR notation"""
    if field.data:
        if '/' not in field.data:
            raise ValidationError('Subnet must be in CIDR notation (e.g., 208.76.80.0/25)')
        
        parts = field.data.split('/')
        if len(parts) != 2:
            raise ValidationError('Invalid CIDR notation')
        
        try:
            cidr = int(parts[1])
            if cidr < 8 or cidr > 32:
                raise ValidationError('CIDR must be between /8 and /32')
        except ValueError:
            raise ValidationError('Invalid CIDR value')

# ========== VLAN FORM ==========

class VLANForm(FlaskForm):
    """
    Form for creating/editing VLANs
    """
    # ========== VLAN IDENTIFICATION ==========
    vlan_id = IntegerField('VLAN ID',
                          validators=[DataRequired(), validate_vlan_id],
                          render_kw={'placeholder': 'Enter VLAN ID (1-4094)'})
    
    name = StringField('VLAN Name',
                      validators=[DataRequired(), Length(max=100)],
                      render_kw={'placeholder': 'e.g., Vlan201, Customer-VLAN-100'})
    
    description = StringField('Description',
                            validators=[Optional(), Length(max=255)],
                            render_kw={'placeholder': 'Detailed description of VLAN purpose'})
    
    # ========== VLAN PURPOSE ==========
    purpose = SelectField('Purpose',
                         choices=VLAN_PURPOSES,
                         validators=[DataRequired()],
                         default='infrastructure')
    
    # ========== STATUS ==========
    status = SelectField('Status',
                        choices=VLAN_STATUS,
                        default='active')
    
    # ========== LOCATION ==========
    datacenter_id = SelectField('Data Center',
                               coerce=int,
                               validators=[Optional()])
    
    # ========== NOTES ==========
    notes = TextAreaField('Notes',
                         validators=[Optional()],
                         render_kw={'rows': 3})


# ========== VLAN SUBNET FORM ==========

class VLANSubnetForm(FlaskForm):
    """
    Form for adding subnets to VLANs
    """
    # ========== SUBNET DEFINITION ==========
    subnet = StringField('Subnet (CIDR)',
                        validators=[DataRequired(), validate_subnet_cidr],
                        render_kw={'placeholder': '208.76.80.0/25', 'class': 'mono'})
    
    gateway = StringField('Gateway IP',
                         validators=[DataRequired(), IPAddress(ipv4=True, ipv6=False)],
                         render_kw={'placeholder': '208.76.80.1 or 208.76.80.254', 'class': 'mono'})
    
    # ========== PRIMARY/SECONDARY ==========
    is_primary = BooleanField('Primary Subnet',
                            default=True,
                            description='Check if this is the primary subnet for the VLAN')
    
    # ========== METADATA ==========
    notes = TextAreaField('Notes',
                         validators=[Optional()],
                         render_kw={'rows': 2, 'placeholder': 'Optional notes about this subnet'})


# ========== ROUTER CONFIG IMPORT FORM ==========

class RouterConfigImportForm(FlaskForm):
    """
    Form for importing router configuration
    """
    config_text = TextAreaField('Router Configuration',
                              validators=[DataRequired()],
                              render_kw={
                                  'rows': 20,
                                  'placeholder': 'Paste the output of "show running-config" here...',
                                  'class': 'mono'
                              })
    
    datacenter_id = SelectField('Data Center',
                               coerce=int,
                               validators=[Optional()],
                               description='Assign all imported VLANs to this data center')
    
    overwrite = BooleanField('Overwrite Existing VLANs',
                           default=False,
                           description='Update existing VLANs if they already exist')


# ========== ARIN CSV IMPORT FORM ==========

class ARINImportForm(FlaskForm):
    """
    Form for importing ARIN allocations from CSV
    """
    csv_data = TextAreaField('CSV Data',
                           validators=[DataRequired()],
                           render_kw={
                               'rows': 15,
                               'placeholder': 'Paste ARIN allocation CSV data here...\n'
                                            'Net Handle,Net Range,Net Type,Net Name,Org ID,Org Name,...',
                               'class': 'mono'
                           })
    
    datacenter_id = SelectField('Data Center',
                               coerce=int,
                               validators=[Optional()],
                               description='Assign all imported ranges to this data center')
    
    create_vlans = BooleanField('Auto-create VLANs',
                              default=False,
                              description='Automatically create VLANs for colocation ranges')


# ========== VLAN SEARCH FORM ==========

class VLANSearchForm(FlaskForm):
    """
    Form for searching/filtering VLANs
    """
    search = StringField('Search',
                        validators=[Optional()],
                        render_kw={'placeholder': 'VLAN ID, name, or subnet...'})
    
    purpose = SelectField('Purpose',
                         choices=[('all', 'All Purposes')] + VLAN_PURPOSES,
                         default='all')
    
    status = SelectField('Status',
                        choices=[('all', 'All Status')] + VLAN_STATUS,
                        default='all')
    
    has_secondary = SelectField('Secondary Subnets',
                              choices=[
                                  ('all', 'All VLANs'),
                                  ('yes', 'Has Secondary Subnets'),
                                  ('no', 'Primary Only')
                              ],
                              default='all')
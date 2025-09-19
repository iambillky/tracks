from app import app, db
from models.server import ServerNetworkConnection
from models.switch_port import SwitchPort

def fix_existing_connections():
    with app.app_context():
        print("Fixing existing server connections...")
        
        connections = ServerNetworkConnection.query.all()
        fixed = 0
        
        for conn in connections:
            # Get the port number - handle if switch_port is an object
            if hasattr(conn.switch_port, 'port_number'):
                port_number = conn.switch_port.port_number
            else:
                port_number = conn.switch_port
            
            # Skip if no valid port number
            if not port_number or not conn.switch_id:
                continue
                
            # Find the switch port
            port = SwitchPort.query.filter_by(
                switch_id=conn.switch_id,
                port_number=port_number
            ).first()
            
            if port:
                # Update the port to show it's connected
                if not port.connected_device_type:
                    port.connected_device_type = 'server'
                    port.connected_device_id = conn.server_id
                    port.description = f"Server connection"
                    
                    # Make sure connection has the port ID
                    if not conn.switch_port_id:
                        conn.switch_port_id = port.id
                    
                    fixed += 1
                    print(f"Fixed port {port_number} on switch {conn.switch_id}")
        
        db.session.commit()
        print(f"Fixed {fixed} connections total")

if __name__ == "__main__":
    fix_existing_connections()
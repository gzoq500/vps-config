#!/usr/bin/env python3
"""Fix AdGuard Home YAML config programmatically."""
import yaml

def fix_adguard_config(config_path='/opt/AdGuardHome/AdGuardHome.yaml'):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Fix dns section
    if 'dns' in config:
        config['dns']['bind_hosts'] = ['0.0.0.0']
        config['dns']['port'] = 53
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Config fixed: {config_path}")

if __name__ == '__main__':
    fix_adguard_config()

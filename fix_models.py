#!/usr/bin/env python3
"""
Fix Django model app_label issues for Galaxy NG.
This script patches models that are missing explicit app_label declarations.
"""

import re
import sys
import os

def fix_service_id_model(file_path):
    """Fix ServiceID model in service_identifier.py"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add Meta class after ServiceID class declaration
        pattern = r'(class ServiceID\(models\.Model\):)'
        replacement = r'\1\n    class Meta:\n        app_label = "ansible_base"'
        
        if 'class Meta:' not in content:
            content = re.sub(pattern, replacement, content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Fixed ServiceID model in {file_path}")
        else:
            print(f"ServiceID model already has Meta class in {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

def fix_resource_models(file_path):
    """Fix ResourceType and Resource models in resource.py"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix ResourceType model - add return None after except and Meta class
        pattern = r'(except ObjectDoesNotExist:)\s*$'
        replacement = r'\1\n        return None\n\n    class Meta:\n        app_label = "ansible_base"'
        
        if 'return None' not in content:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Fix Resource model - add app_label before unique_together
        pattern = r'(\s+)(unique_together = )'
        replacement = r'\1app_label = "ansible_base"\n\1\2'
        
        if 'app_label = "ansible_base"' not in content:
            content = re.sub(pattern, replacement, content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Fixed Resource models in {file_path}")
        else:
            print(f"Resource models already fixed in {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

def fix_content_type_model(file_path):
    """Fix DABContentType model in content_type.py"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Add app_label before unique_together
        pattern = r'(\s+)(unique_together = )'
        replacement = r'\1app_label = "dab_rbac"\n\1\2'
        
        if 'app_label = "dab_rbac"' not in content:
            content = re.sub(pattern, replacement, content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Fixed DABContentType model in {file_path}")
        else:
            print(f"DABContentType model already fixed in {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

def main():
    venv_path = os.environ.get('VIRTUAL_ENV', '/venv')
    base_path = f"{venv_path}/lib/python3.11/site-packages"
    
    # Fix ServiceID model
    service_id_path = f"{base_path}/ansible_base/resource_registry/models/service_identifier.py"
    if os.path.exists(service_id_path):
        fix_service_id_model(service_id_path)
    
    # Fix Resource models
    resource_path = f"{base_path}/ansible_base/resource_registry/models/resource.py"
    if os.path.exists(resource_path):
        fix_resource_models(resource_path)
    
    # Fix DABContentType model
    content_type_path = f"{base_path}/ansible_base/rbac/models/content_type.py"
    if os.path.exists(content_type_path):
        fix_content_type_model(content_type_path)
    
    print("Model fixing complete!")

if __name__ == "__main__":
    main()
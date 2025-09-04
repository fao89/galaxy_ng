"""
Setup test data for filesystem-based galaxy_ng.
"""
import os
from django.contrib.auth import get_user_model
from galaxy_ng.app.models_fs import Namespace

User = get_user_model()

# Create test namespaces
test_namespaces = [
    {
        'name': 'community',
        'description': 'Community collections namespace',
        'company': 'Ansible Community',
        'email': 'community@ansible.com',
    },
    {
        'name': 'redhat',
        'description': 'Red Hat certified collections',
        'company': 'Red Hat, Inc.',
        'email': 'ansible@redhat.com',
    },
    {
        'name': 'testing',
        'description': 'Testing and development namespace',
        'company': 'Galaxy NG Development',
        'email': 'dev@galaxy.example.com',
    }
]

print("Creating test namespaces...")
for ns_data in test_namespaces:
    namespace, created = Namespace.objects.get_or_create(
        name=ns_data['name'],
        defaults=ns_data
    )
    if created:
        print(f"✓ Created namespace: {namespace.name}")
    else:
        print(f"- Namespace already exists: {namespace.name}")

# Create content directories if they don't exist
content_root = os.environ.get('GALAXY_CONTENT_ROOT', '/content')
os.makedirs(f"{content_root}/collections", exist_ok=True)
os.makedirs(f"{content_root}/repositories/staging/collections", exist_ok=True) 
os.makedirs(f"{content_root}/repositories/approved/collections", exist_ok=True)
os.makedirs(f"{content_root}/metadata", exist_ok=True)

print(f"✓ Created content directories in {content_root}")

# Create filesystem namespace directories
for ns_data in test_namespaces:
    ns_dir = f"{content_root}/collections/{ns_data['name']}"
    os.makedirs(ns_dir, exist_ok=True)
    print(f"✓ Created namespace directory: {ns_dir}")

print("Filesystem-based galaxy_ng setup complete!")
print(f"Content root: {content_root}")
print("Available namespaces:", [ns['name'] for ns in test_namespaces])
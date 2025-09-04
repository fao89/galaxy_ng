#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'minimal_migration_settings')
os.environ['POSTGRES_DB'] = 'galaxy_ng'
os.environ['POSTGRES_USER'] = 'galaxy_ng'
os.environ['POSTGRES_PASSWORD'] = 'galaxy_ng'
os.environ['DATABASES__default__HOST'] = 'postgres'
os.environ['DATABASES__default__PORT'] = '5432'

django.setup()

from galaxy_ng.app_fs.models import User

try:
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin'
    )
    print(f"Superuser {user.username} created successfully")
except Exception as e:
    print(f"Error creating superuser: {e}")
    # Try to get existing user
    try:
        user = User.objects.get(username='admin')
        print(f"Superuser {user.username} already exists")
    except User.DoesNotExist:
        print("Failed to create or find admin user")
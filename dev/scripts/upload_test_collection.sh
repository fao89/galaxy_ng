#!/bin/bash
# Upload a test collection to the filesystem-based galaxy_ng

set -e

API_ROOT="${HUB_API_ROOT:-http://localhost:5001/api/galaxy/}"
USERNAME="${DJANGO_SUPERUSER_USERNAME:-admin}"
PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}"

echo "Testing Collection Upload to Filesystem Galaxy NG"
echo "=============================================="
echo "API Root: $API_ROOT"
echo "Username: $USERNAME"
echo ""

# Create a temporary test collection
TEMP_DIR=$(mktemp -d)
COLLECTION_DIR="$TEMP_DIR/test_collection"

echo "Creating test collection in $TEMP_DIR..."

# Create collection structure
mkdir -p "$COLLECTION_DIR/plugins/modules"
mkdir -p "$COLLECTION_DIR/roles/test_role/tasks"

# Create galaxy.yml
cat > "$COLLECTION_DIR/galaxy.yml" << EOF
namespace: testing
name: filesystem_test
version: 1.0.0
description: Test collection for filesystem-based galaxy_ng
authors:
  - Galaxy NG Development Team
license:
  - GPL-3.0-or-later
tags:
  - testing
  - filesystem
dependencies: {}
repository: https://github.com/ansible/galaxy_ng
documentation: https://galaxy_ng.readthedocs.io
homepage: https://github.com/ansible/galaxy_ng
issues: https://github.com/ansible/galaxy_ng/issues
EOF

# Create a simple module
cat > "$COLLECTION_DIR/plugins/modules/test_module.py" << 'EOF'
#!/usr/bin/python
DOCUMENTATION = '''
module: test_module
short_description: Test module for filesystem collection
description: A simple test module
options:
  message:
    description: Message to return
    type: str
    default: "Hello from filesystem!"
'''

EXAMPLES = '''
- name: Test the module
  testing.filesystem_test.test_module:
    message: "Hello World"
'''

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
        argument_spec={
            'message': {'type': 'str', 'default': 'Hello from filesystem!'}
        }
    )
    
    message = module.params['message']
    module.exit_json(changed=False, message=message)

if __name__ == '__main__':
    main()
EOF

# Create a simple role
cat > "$COLLECTION_DIR/roles/test_role/tasks/main.yml" << EOF
---
- name: Test task
  debug:
    msg: "This is a test role in the filesystem collection"
EOF

# Create README
cat > "$COLLECTION_DIR/README.md" << EOF
# Testing Filesystem Test Collection

This is a test collection for the filesystem-based galaxy_ng implementation.

## Modules

- \`test_module\`: A simple test module

## Roles

- \`test_role\`: A simple test role
EOF

# Build collection archive
echo "Building collection archive..."
cd "$COLLECTION_DIR"
tar -czf "$TEMP_DIR/testing-filesystem_test-1.0.0.tar.gz" *

echo "Collection archive created: $TEMP_DIR/testing-filesystem_test-1.0.0.tar.gz"
echo "Archive size: $(du -h "$TEMP_DIR/testing-filesystem_test-1.0.0.tar.gz" | cut -f1)"

# Upload collection
echo ""
echo "Uploading collection to Galaxy NG..."

UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -u "$USERNAME:$PASSWORD" \
    -X POST \
    -F "file=@$TEMP_DIR/testing-filesystem_test-1.0.0.tar.gz" \
    "${API_ROOT}v3/artifacts/collections/")

HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$UPLOAD_RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
echo "Response:"
echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"

if [ "$HTTP_CODE" = "202" ]; then
    # Extract task ID
    TASK_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['task'])" 2>/dev/null || echo "")
    
    if [ -n "$TASK_ID" ]; then
        echo ""
        echo "Upload accepted! Task ID: $TASK_ID"
        echo "Monitoring task progress..."
        
        # Monitor task progress
        for i in {1..30}; do
            sleep 2
            TASK_RESPONSE=$(curl -s -u "$USERNAME:$PASSWORD" "${API_ROOT}v3/tasks/$TASK_ID/")
            TASK_STATE=$(echo "$TASK_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])" 2>/dev/null || echo "unknown")
            
            echo "Task state: $TASK_STATE"
            
            if [ "$TASK_STATE" = "completed" ]; then
                echo "✓ Collection upload completed successfully!"
                break
            elif [ "$TASK_STATE" = "failed" ]; then
                echo "✗ Collection upload failed!"
                echo "Task details:"
                echo "$TASK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TASK_RESPONSE"
                break
            fi
        done
    fi
else
    echo "✗ Upload failed with HTTP $HTTP_CODE"
fi

# Test collection listing
echo ""
echo "Testing collection listing..."
LIST_RESPONSE=$(curl -s -u "$USERNAME:$PASSWORD" "${API_ROOT}v3/collections/testing/filesystem_test/")
echo "Collection details:"
echo "$LIST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LIST_RESPONSE"

# Clean up
echo ""
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "Test complete!"
echo ""
echo "You can now:"
echo "  - View the collection: ${API_ROOT}v3/collections/testing/filesystem_test/"
echo "  - Download it: ${API_ROOT}v3/collections/testing/filesystem_test/versions/1.0.0/download/"
echo "  - Check validation: docker compose -f dev/compose/standalone-fs.yaml exec manager python /src/manage.py validate_collections --namespace testing"
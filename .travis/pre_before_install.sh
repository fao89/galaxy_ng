# This file is sourced by .travis/before_install.sh

if [[ "$TRAVIS_PULL_REQUEST" != 'false' ]]; then
  pip install requests
  python .travis/custom_check_pull_request.py
fi

# Unpin pulpcore and pulp-ansible
sed -i '0,/pulpcore/{s/pulpcore.*/pulpcore",/}' setup.py
sed -i '0,/pulp-ansible/{s/pulp-ansible.*/pulp-ansible",/}' setup.py

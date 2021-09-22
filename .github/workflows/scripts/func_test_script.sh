#!/usr/bin/env bash
# coding=utf-8

set -mveuo pipefail

pytest -v -r sx --color=yes --pyargs galaxy_ng.tests.functional

pip install ../pulp_ansible
pip install -r ../pulp_ansible/functest_requirements.txt

pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.functional

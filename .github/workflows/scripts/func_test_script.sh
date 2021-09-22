#!/usr/bin/env bash
# coding=utf-8

set -mveuo pipefail

pytest -v -r sx --color=yes --pyargs galaxy_ng.tests.functional

cd ../pulp_ansible
pip install .
pip install -r functest_requirements.txt

pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.functional

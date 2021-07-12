# This file is meant to be sourced by ci-scripts

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github galaxy_ng' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

PULP_CI_CONTAINER=pulp

# Run a command
cmd_prefix() {
  docker exec "$PULP_CI_CONTAINER" "$@"
}

# Run a command, and pass STDIN
cmd_stdin_prefix() {
  docker exec -i "$PULP_CI_CONTAINER" "$@"
}

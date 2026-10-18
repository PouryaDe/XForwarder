#!/usr/bin/env bash
#
# Forward-Manager compatibility wrapper -> redirects to XForwarder
#

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
exec bash "$SCRIPT_DIR/xforwarder.sh" "$@"

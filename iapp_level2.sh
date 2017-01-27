#!/bin/bash
#
# Wrapper script for iapp_level2.py, which runs the 
# CSPP IAPP package.
#
# Environment settings:
# CSPP_RT_HOME : the location of the CSPP_RT directory
#
# Copyright 2014-2014, University of Wisconsin Regents.
# Licensed under the GNU GPLv3.

if [ -z "$CSPP_IAPP_HOME" ]; then
    echo "CSPP_IAPP_HOME is not set, but is required for this script to operate."
    exit 9
fi

. ${CSPP_IAPP_HOME}/cspp_iapp_runtime.sh

usage() {
    $PY $CSPP_IAPP_HOME/scripts/iapp_level2.py --help
}

if [ -z "$1" ]; then
    usage
    exit 3
fi

$PY $CSPP_IAPP_HOME/scripts/iapp_level2.py "$@"

exit $?

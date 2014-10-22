#!/bin/bash
# $Id$
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

#
# Gather the various command line options...
#

INPUT_FILES_OPT=
SAT_OPT=
WORK_DIR_OPT=
TOPO_FILE_OPT=
INSTR_OPT=
RETR_MTHD_OPT=
PROC_OPT=
DEBUG_OPT=
VERBOSITY_OPT=

#echo $@

OPTS=`getopt -o "i:s:w:t:p:dvh" -l "input_files:,satellite:,work_directory:,topo_file:,instrument_combo:,retrieval_method:,processors:,debug,verbose,help" -- "$@"`

# If returncode from getopt != 0, exit with error.
if [ $? != 0 ]
then
    echo "There was an error with the command line parameters to iapp_level2.sh, aborting..."
    exit 1
fi

# A little magic
eval set -- "$OPTS"

# Now go through all the options
haveFlag=0
helpFlag=0
usageFlag=0

while true ;
do
    case "$1" in
        -i|--input_files)
            INPUT_FILES_OPT="--input_files=$2"
            #echo "Setting INPUT_FILES_OPT"
            haveFlag=1
            shift 2;;

        -s|--satellite)
            SAT_OPT="--satellite=$2"
            #echo "Setting SAT_OPT"
            haveFlag=1
            shift 2;;

        -w|--work_directory)
            WORK_DIR_OPT="--work_directory=$2"
            #echo "Setting WORK_DIR_OPT"
            haveFlag=1
            shift 2;;

        -t|--topo_file)
            TOPO_FILE_OPT="--topo_file=$2"
            #echo "Setting TOPO_FILE_OPT"
            haveFlag=1
            shift 2;;

        --instrument_combo)
            PROC_OPT="--instrument_combo=$2"
            #echo "Setting INSTR_OPT"
            haveFlag=1
            shift 2;;

        --retrieval_method)
            PROC_OPT="--retrieval_method=$2"
            #echo "Setting RETR_MTHD_OPT"
            haveFlag=1
            shift 2;;

        -p|--processors)
            PROC_OPT="--processors=$2"
            #echo "Setting PROC_OPT"
            haveFlag=1
            shift 2;;

        -d|--debug)
            DEBUG_OPT="--debug"
            #echo "Setting DEBUG_OPT"
            haveFlag=1
            shift ;;

        -v|--verbose)
            VERBOSITY_OPT="-"$(echo $VERBOSITY_OPT | sed s#-##)"v"
            #echo "Setting VERBOSITY_OPT"
            haveFlag=1
            shift ;;

        -h|--help)
            if [[ $haveFlag -eq 0 ]];
            then
                helpFlag=1
            fi
            shift;
            break ;;

        --)
            if [[ $haveFlag -eq 0 ]];
            then
                usageFlag=1
            fi
            shift;
            break;;

    esac
done

if [[ $helpFlag -eq 1 ]];
then
    $PY $CSPP_IAPP_HOME/iapp/iapp_level2.py -h
    exit 0
fi
if [[ $usageFlag -eq 1 ]];
then
    $PY $CSPP_IAPP_HOME/iapp/iapp_level2.py -h
    exit 0
fi

echo "INPUT_FILES_OPT      = "$INPUT_FILES_OPT
echo "SAT_OPT              = "$SAT_OPT
echo "WORK_DIR_OPT         = "$WORK_DIR_OPT
echo "TOPO_FILE_OPT        = "$TOPO_FILE_OPT
echo "INSTR_OPT            = "$INSTR_OPT
echo "RETR_MTHD_OPT        = "$RETR_MTHD_OPT
echo "PROC_OPT             = "$PROC_OPT
echo "DEBUG_OPT            = "$DEBUG_OPT
echo "VERBOSITY_OPT        = "$VERBOSITY_OPT

echo "$PY $CSPP_IAPP_HOME/iapp/iapp_level2.py \
    $INPUT_FILES_OPT \
    $SAT_OPT \
    $WORK_DIR_OPT \
    $TOPO_FILE_OPT \
    $INSTR_OPT \
    $RETR_MTHD_OPT \
    $PROC_OPT \
    $DEBUG_OPT \
    $VERBOSITY_OPT
"

#exit 1

$PY $CSPP_IAPP_HOME/iapp/iapp_level2.py \
    $INPUT_FILES_OPT \
    $SAT_OPT \
    $WORK_DIR_OPT \
    $TOPO_FILE_OPT \
    $INSTR_OPT \
    $RETR_MTHD_OPT \
    $PROC_OPT \
    $DEBUG_OPT \
    $VERBOSITY_OPT -vv

##############################
#         Packaging          #
##############################

#bash $CSPP_RT_HOME/../CSPP_RT_repo/trunk/scripts/edr/CSPP_RT_ViirsEdrMasks_Package.sh  $CSPP_RT_HOME/viirs/edr/viirs_edr.sh ../../sample_data/viirs/edr/input/VIIRS_OPS_unpackTest/HDF5/

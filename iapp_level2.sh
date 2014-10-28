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

OPTS=`getopt -o "i:w:t:f:r:s:dvh" -l "input_files:,satellite:,work_directory:,topography_file:,forecast_file:,radiosonde_file:,surface_obs_file:,instrument_combo:,retrieval_method:,print_retrieval,print_l1d_header,debug,verbose,help" -- "$@"`

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

        --satellite)
            SAT_OPT="--satellite=$2"
            #echo "Setting SAT_OPT"
            haveFlag=1
            shift 2;;

        -w|--work_directory)
            WORK_DIR_OPT="--work_directory=$2"
            #echo "Setting WORK_DIR_OPT"
            haveFlag=1
            shift 2;;

        -t|--topography_file)
            TOPO_FILE_OPT="--topography_file=$2"
            #echo "Setting TOPO_FILE_OPT"
            haveFlag=1
            shift 2;;

        -f|--forecast_file)
            FORECAST_FILE_FILE_OPT="--forecast_file=$2"
            #echo "Setting FORECAST_FILE_FILE_OPT"
            haveFlag=1
            shift 2;;

        -r|--radiosonde_file)
            RADIOSONDE_FILE_OPT="--radiosonde_file=$2"
            #echo "Setting RADIOSONDE_FILE_OPT"
            haveFlag=1
            shift 2;;

        -s|--surface_obs_file)
            SURFACE_OBS_FILE_OPT="--surface_obs_file=$2"
            #echo "Setting SURFACE_OBS_FILE_OPT"
            haveFlag=1
            shift 2;;

        --instrument_combo)
            INSTR_OPT="--instrument_combo=$2"
            #echo "Setting INSTR_OPT"
            haveFlag=1
            shift 2;;

        --retrieval_method)
            RETR_MTHD_OPT="--retrieval_method=$2"
            #echo "Setting RETR_MTHD_OPT"
            haveFlag=1
            shift 2;;

        --print_retrieval)
            PRINT_RETRIEVAL_OPT="--print_retrieval"
            #echo "Setting PRINT_RETRIEVAL_OPT"
            haveFlag=1
            shift ;;

        --print_l1d_header)
            PRINT_L1D_OPT="--print_l1d_header"
            #echo "Setting PRINT_L1D_OPT"
            haveFlag=1
            shift ;;

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

#echo "INPUT_FILES_OPT      = "$INPUT_FILES_OPT
#echo "SAT_OPT              = "$SAT_OPT
#echo "WORK_DIR_OPT         = "$WORK_DIR_OPT
#echo "TOPO_FILE_OPT        = "$TOPO_FILE_OPT
#echo "FORECAST_FILE_OPT    = "$FORECAST_FILE_FILE_OPT
#echo "RADIOSONDE_FILE_OPT  = "$RADIOSONDE_FILE_OPT
#echo "SURFACE_OBS_FILE_OPT = "$SURFACE_OBS_FILE_OPT
#echo "INSTR_OPT            = "$INSTR_OPT
#echo "RETR_MTHD_OPT        = "$RETR_MTHD_OPT
#echo "DEBUG_OPT            = "$DEBUG_OPT
#echo "PRINT_RETRIEVAL_OPT  = "$PRINT_RETRIEVAL_OPT
#echo "PRINT_L1D_OPT        = "$PRINT_L1D_OPT
#echo "VERBOSITY_OPT        = "$VERBOSITY_OPT

#echo "$PY $CSPP_IAPP_HOME/iapp/iapp_level2.py \
    #$INPUT_FILES_OPT \
    #$SAT_OPT \
    #$WORK_DIR_OPT \
    #$TOPO_FILE_OPT \
    #$FORECAST_FILE_FILE_OPT \
    #$RADIOSONDE_FILE_OPT \
    #$SURFACE_OBS_FILE_OPT \
    #$INSTR_OPT \
    #$RETR_MTHD_OPT \
    #$PRINT_RETRIEVAL_OPT \
    #$PRINT_L1D_OPT \
    #$DEBUG_OPT \
    #$VERBOSITY_OPT
#"

#exit 1

$PY $CSPP_IAPP_HOME/iapp/iapp_level2.py \
    $INPUT_FILES_OPT \
    $SAT_OPT \
    $WORK_DIR_OPT \
    $TOPO_FILE_OPT \
    $FORECAST_FILE_FILE_OPT \
    $RADIOSONDE_FILE_OPT \
    $SURFACE_OBS_FILE_OPT \
    $INSTR_OPT \
    $RETR_MTHD_OPT \
    $PRINT_RETRIEVAL_OPT \
    $PRINT_L1D_OPT \
    $DEBUG_OPT \
    $VERBOSITY_OPT -vv

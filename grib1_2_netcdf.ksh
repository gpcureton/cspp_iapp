#!/bin/ksh
#
# =================================================================================
#   (C) 1998-2005  Cooperative Institute for Meteorological Satellite Studies
#                  University of Wisconsin-Madison, Madison, Wisconsin, USA

#   This file is part of the International ATOVS Processing Package (IAPP).

#   IAPP is free software; you can redistribute it and/or modify it under the terms
#   of the GNU General Public License as published by the Free Software Foundation;
#   either version 2 of the License, or (at your option) any later version.

#   IAPP is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with this
#   program; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
#   Suite 330, Boston, MA  02111-1307  USA
# =================================================================================
#
#
# NAME:
#       iapp_grib2nc
#
# PURPOSE:
#       Korn shell script to extract meteorological ancillary data from
#         "aviation" GRIB files
#
# CATEGORY:
#       IAPP: Ancillary
#
# LANGUAGE:
#       Korn shell script
#
# CALLING SEQUENCE:
#       iapp_grib2nc grib_input cdl_input
#
# INPUTS:
#       grib_input:   AVN (GFS, also called "aviation") model output GRIB file with name of the form
#
#                         avn_YYMMDD_TT_HH
#
#                     where YYMMDD [year (last two digits), month, day] is the cycle date,
#                     TT [e.g., 00 (UTC)] is the cycle time from which the forecast was run, and
#                     HH denotes the reanalysis (00) or the forecast time (06,12,etc.) in hours.
#
#       cdl_input:    CDL file from which the required grib file parameters are read.
#                       The parameters are stored as a string in the variable attribute
#                       "grib_parameter".
#
# OUTPUTS:
#       The shell script produces two output files. Both are required by the 
#       Fortran-90 code that writes the binary data to the netCDF file.
#       The files created are
#
#         ancillary.info:   This file contains information defining global
#                             attributes to write to the output file and also
#                             the required variable names defined in the CDL file.
#         ancillary.data:   Binary file containing the required parameters as 32 bit
#                             floating point arrays, each array having 360x181 elements
#                             on a 1x1 degree global grid
#                             (latitude 90.0 to -90.0 in 1.0 degree steps)
#                             (longitude 0.0 to -1.0 in 1.0 degree steps)
#
#       Both files are deleted upon exit.
#
# CALLS:
#       This script invokes the Fortran program iapp_bin2nc to convert the GRIB
#       format data to netCDF.
#
# SIDE EFFECTS:
#
# RESTRICTIONS:
#
# PROCEDURE:
#       GRIB extraction is done using wgrib (see http://wesley.wwb.noaa.gov)
#
# EXAMPLE:
#
# MODIFICATION HISTORY:
#       Written by:   Liam Gumley, CIMSS/SSEC, 04-Jun-1997
#
#                     Paul van Delst, CIMSS/SSEC, 24-Apr-1998
#                     paul.vandelst@ssec.wisc.edu
#                     - Converted from csh to ksh script
#
#                     Harold Woolf, CIMSS/SSEC, 19-Apr-2005 ff.
#                     hal.woolf@ssec.wisc.edu
#                     - Modified to work in Linux
#
# ------------------------------------------------------------------------------------------

#export PATH=/usr/local/bin:/usr/bin:/bin:/usr/X11R6/bin:$HOME/bin:.

##################################
#bdir=/home/chial/Hal_iapp/decoders/bin
#ndir=/opt/netcdf-3.6-gfortran/bin
bdir=$DECODERS/bin
ndir=/usr/bin
##################################

 
wgrib=$bdir/wgrib
readparm=$bdir/readparm
iapp_bin2nc=$bdir/iapp_bin2nc

# -------------------------------------
# Check for correct number of arguments
# -------------------------------------

  if [ $# -ne 3 ]; then

    echo
    echo 'Usage: iapp_grib2nc <grib_input> <cdl_input>'
    echo
    echo '     grib_input    GFS GRIB file; only grid type 3 (global 1 deg. resolution) accepted.'
    echo '     cdl_input     CDL file from which the required grib file parameters are read.'
    echo '                   The parameters are stored as a string in the variable attribute'
    echo '                   "grib_parameter".'
    echo

    exit 1

  fi

# -------------
# Get arguments
# -------------

  grib_file=$1
  if [ ! -f ${grib_file} ]; then
    echo 'GRIB file '${grib_file}' not found'
    exit 1
  fi

  cdl_file=$2
  if [ ! -f ${cdl_file} ]; then
    echo 'CDL file '${cdl_file}' not found'
    exit 1
  fi

  nc_file_cm=$3

# ----------------------------------------------
# Check that we have the correct grid dimensions
# ----------------------------------------------

# -- Get longitude dimension

   longitude=`grep "Number of longitudes" ${cdl_file} | cut -f1 -d\; | cut -f2 -d\= | cut -c2-4`

# -- Get latitude dimension

   latitude=`grep "Number of latitudes" ${cdl_file} | cut -f1 -d\; | cut -f2 -d\= | cut -c2-4`

# -- Perform check

  grid_dim='nx '${longitude}' ny '${latitude}
  echo 'Checking for correct grid dimensions, '${grid_dim}

#  $wgrib ${grib_file} -V | tail +2 | grep "${grid_dim}" >/dev/null 2>&1

#  if [ $? -ne 0 ]; then
#    echo 'Unexpected grid dimensions'
#    exit 1
#  fi

# ----------------------
# Get the GRIB file date
# ----------------------

  grib_date=$($wgrib ${grib_file} -4yr | head -1 | cut -f3 -d: | sed 's/d=//')

# ---------------------------
# Get the forecast descriptor
# ---------------------------

  grib_forecast=$($wgrib ${grib_file} -v | head -1 | cut -f7 -d: | sed 's/ /_/')

  echo 'GRIB file forecast/analysis : '${grib_forecast}

# -------------------------------
# Construct the output file names
# -------------------------------

  out_file='ancillary.data'
  #nc_file='iapp_ancillary_'${grib_date}'-'${grib_forecast}'.nc'
  nc_file=$nc_file_cm

# ------------------------------------
# Extract the selected GRIB parameters
# ------------------------------------

  echo 'Extracting selected parameters from GRIB file '${grib_file}

# ----------------------------------------------------------------------------
# Create a list of parameters to be extracted and determine the number thereof
# ----------------------------------------------------------------------------

  grep "grib_parameter" ${cdl_file} | cut -f2 -d\" > gribparm.lis
  nparam=`wc -l gribparm.lis | cut -f1 -d" "`

# -----------------------------------
# Loop through the desired parameters
# -----------------------------------

  n_grib_parameters=0

  while [ ${n_grib_parameters} -lt ${nparam} ]; do

#   ---------------------------
#   Increment parameter counter
#   ---------------------------

    let n_grib_parameters=n_grib_parameters+1

    parameter=`$readparm ${n_grib_parameters}`

#   --------------------------
#   Print out what's happening
#   --------------------------

    echo '  Extracting parameter - '${parameter}

#   -----------------------------------------------------------
#   Dump the current parameter data to a binary file, no header
#   -----------------------------------------------------------

    $wgrib ${grib_file} -s | grep "${parameter}" | $wgrib ${grib_file} -i -bin -nh -append -o ${out_file} >/dev/null 2>&1

    if [ $? -ne 0 ]; then
      echo 'Error writing to '${out_file}
      exit 1
    fi

  done

  echo 'Number of parameters extracted = '${n_grib_parameters}

# ------------------------------------------------------------
# Create a temporary file containing input for the data reader
# ------------------------------------------------------------

  info_file='ancillary.info'

# -- List the global attribute names to add to the netCDF output file --

  echo 'Number of global attributes to add to netCDF file (values follow):4;' > ${info_file}
  echo 'creation_date:'$(date -u)';'  >> ${info_file}
  echo 'data_source:'${grib_file}';'  >> ${info_file}
  echo 'yyyymmddhh:'${grib_date}';'   >> ${info_file}
  echo 'forecast:'${grib_forecast}';' >> ${info_file}

# -- Output the number of long. and lat. points for array allocation --

  echo 'Number of GRIB longitudes:'${longitude}';' >> ${info_file}
  echo 'Number of GRIB latitudes:'${latitude}';'   >> ${info_file}

# -- Output the number and names of the GRIB file parameters to extract --

  echo 'Number of GRIB parameters extracted (netCDF names follow):'${n_grib_parameters}';' >> ${info_file}
  grep "grib_parameter" ${cdl_file} | cut -f1 -d: >> ${info_file}

  if [ $? -ne 0 ]; then
    echo 'Error writing to temporary file '${info_file}
    exit 1
  fi

# ---------------------------------------
# Create an empty netCDF file using ncgen
# ---------------------------------------

  $ndir/ncgen -b -o ${nc_file} ${cdl_file}

  if [ $? -ne 0 ]; then
    echo 'Error creating netCDF file '${nc_file}
    exit 1
  fi

# --------------------------------------------------------------
# Invoke the program iapp_bin2nc to write data to netCDF output
# --------------------------------------------------------------

$iapp_bin2nc << EOF
${info_file}
${out_file}
${nc_file}
EOF

  if [ $? -ne 0 ]; then
    echo 'Error writing to netCDF file '${nc_file}
    exit 1
  fi

# -----------------
# Exit with success
# -----------------

rm gribparm.lis

exit 0

#!/bin/ksh
#
# =================================================================================
#   (C) 2008  Cooperative Institute for Meteorological Satellite Studies
#             University of Wisconsin-Madison, Madison, Wisconsin, USA

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
#       iappgrib2_nc.ksh
#
# PURPOSE:
#       Korn shell script to extract meteorological ancillary data from
#         "aviation" GRIB2 files
#
# CATEGORY:
#       IAPP: Ancillary
#
# LANGUAGE:
#       Korn shell script
#
# CALLING SEQUENCE:
#       iappgrib2_nc.ksh grib_input cdl_input
#
# INPUTS:
#       grib_input:   AVN (GFS, also called "aviation") model output GRIB2 file with name of the form
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
#       GRIB extraction is done using wgrib2 (see http://www.cpc.ncep.noaa.gov/products/wesley/wgrib2)
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
#                     Harold Woolf, CIMSS/SSEC
#                     hal.woolf@ssec.wisc.edu
#                     - Modified to work in Linux       19-Apr-2005 ff.
#                     - Modified to process grib2 files 23-Jan-2008 ff.
#
#                     Chia Moeller, CIMSS/SSEC
#                     - Modified to work on gorilla  4-2013
#
# ------------------------------------------------------------------------------------------

export PATH=/usr/local/bin:/usr/bin:/bin:/usr/X11R6/bin:$HOME/bin:.

##################################
#bdir=/home/chial/Hal_iapp/decoders/bin
#ndir=/opt/netcdf-3.6-gfortran/bin
bdir=$DECODERS/bin
ndir=/usr/bin
##################################
 
wgrib2=$bdir/wgrib2
readparm=$bdir/readparm
iapp_bin2nc=$bdir/iapp_bin2nc

# -------------------------------------
# Check for correct number of arguments
# -------------------------------------

  if [ $# -ne 2 ]; then

    echo
    echo 'Usage: iappgrib2_nc.ksh <grib_input> <cdl_input>'
    echo
    echo '     grib_input    GFS GRIB2 file, global 1 degree resolution'
    echo '     cdl_input     CDL file (with path) from which the grib file parameters are read.'
    echo '                   The parameters are stored as a string in the variable attribute'
    echo '                   "grib_parameter".'
    echo

    exit 1

  fi

# -------------
# Get arguments
# -------------

  gfile=$1
  if [ ! -f $gfile ]; then
    echo 'GRIB file '$gfile' not found'
    exit 1
  fi

  cfile=$2
  if [ ! -f $cfile ]; then
    echo 'CDL file '$cfile' not found'
    exit 1
  fi

# -----------------------
# Get the grid dimensions
# -----------------------

# -- longitude dimension

   longitude=`grep "Number of longitudes" $cfile | cut -f1 -d\; | cut -f2 -d\= | cut -c2-4`

# -- latitude dimension

   latitude=`grep "Number of latitudes" $cfile | cut -f1 -d\; | cut -f2 -d\= | cut -c2-4`

# ----------------------
# Get the GRIB file date
# ----------------------

  gdate=$($wgrib2 $gfile | head -1 | cut -f3 -d: | sed 's/d=//')

# ---------------------------
# Get the forecast descriptor
# ---------------------------

  gfore=$($wgrib2 $gfile | head -1 | cut -f6 -d: | sed 's/ /_/')
  gfore=`echo $gfore | sed 's/ /_/'`

  if [ $gfore != 'anl' ]; then
     gfore=`echo $gfore | sed 's/_hour/hr/'`
  fi

  echo 'GRIB file forecast/analysis : '$gfore

# -------------------------------
# Construct the output file names
# -------------------------------

  dfile='ancillary.data'
  nfile='iapp_ancillary_'${gdate}'-'${gfore}'.nc'

# ------------------------------------
# Extract the selected GRIB parameters
# ------------------------------------

  echo 'Extracting selected parameters from GRIB file '$gfile

# ----------------------------------------------------------------------------
# Create a list of parameters to be extracted and determine the number thereof
# ----------------------------------------------------------------------------

  grep "grib_parameter" $cfile | cut -f2 -d\" > gribparm.lis
  nparam=`cat gribparm.lis | wc -l`

# -----------------------------------
# Loop through the desired parameters
# -----------------------------------

  ngp=0

  while [ $ngp -lt $nparam ]; do

#   ---------------------------
#   Increment parameter counter
#   ---------------------------

    let ngp=ngp+1

    parameter=`$readparm $ngp`

#   --------------------------
#   Print out what's happening
#   --------------------------

    echo '  Extracting parameter - '$parameter

#   -----------------------------------------------------------
#   Dump the current parameter data to a binary file, no header
#   -----------------------------------------------------------

    line=`$wgrib2 $gfile -s | grep "$parameter"`
    echo $line > textline
    recnum=`awk -F : '{print $1}' textline`
    $wgrib2 $gfile -d $recnum -append -no_header -order we:ns -bin $dfile 2>&1
    rm textline

    if [ $? -ne 0 ]; then
      echo 'Error writing to '$dfile
      exit 1
    fi

  done

  echo 'Number of parameters extracted = '$ngp

# ------------------------------------------------------------
# Create a temporary file containing input for the data reader
# ------------------------------------------------------------

  ifile='ancillary.info'

# -- List the global attribute names to add to the netCDF output file --

  echo 'Number of global attributes to add to netCDF file (values follow):4;' > $ifile
  echo 'creation_date:'$(date -u)';' >> $ifile
  echo 'data_source:'${gfile}';'     >> $ifile
  echo 'yyyymmddhh:'${gdate}';'      >> $ifile
  echo 'forecast:'${gfore}';'        >> $ifile

# -- Output the number of longitude and latitude points for array allocation --

  echo 'Number of GRIB longitudes:'${longitude}';' >> $ifile
  echo 'Number of GRIB latitudes:'${latitude}';'   >> $ifile

# -- Output the number and names of the GRIB file parameters --

  echo 'Number of GRIB parameters extracted (netCDF names follow):'${ngp}';' >> $ifile
  grep "grib_parameter" $cfile | cut -f1 -d: >> $ifile

  if [ $? -ne 0 ]; then
    echo 'Error writing to temporary file '$ifile
    exit 1
  fi

# ---------------------------------------
# Create an empty netCDF file using ncgen
# ---------------------------------------

  $ndir/ncgen -b -o $nfile $cfile

  if [ $? -ne 0 ]; then
    echo 'Error creating netCDF file '$nfile
    exit 1
  fi

# --------------------------------------------------------------
# Invoke the program iapp_bin2nc to write data to netCDF output
# --------------------------------------------------------------

$iapp_bin2nc << EOF
$ifile
$dfile
$nfile
EOF

  if [ $? -ne 0 ]; then
    echo 'Error writing to netCDF file '$nfile
    exit 1
  fi

# -----------------
# Exit with success
# -----------------

rm gribparm.lis

exit 0

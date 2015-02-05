#!/bin/csh

# Example script on how you would run a main script to fetch ancillary
# data given the data date and time in the JPSS/ADL Direct Broadcast
# environment.
#
#  This script uses the geolocation data to get the date/time 
# information needed to match the corresponding ancillary data.  The
# script assumes the geolocation file uses this naming convention:
#
#    GMODO_npp_dYYYYMMDD_tHHMMsss
#      where YYYY is the year
#            MM   is the month
#            DD   is the day of the month
#            HH   is the hour
#            MM   is the minute
#            sss  is the seconds and tenths of seconds (not used)
#
# Written by Kathleen Strabala
# University of Wisconsin-Madison/SSEC  kathy.strabala@ssec.wisc.edu
# June 2011
#
# $Date: 2015-02-05 14:35:32 -0600 (Thu, 05 Feb 2015) $
# $Revision: 2346 $
# $Author: geoffc $
# $HeadURL: https://svn.ssec.wisc.edu/repos/jpss_adl/trunk/util/CSPP/IAPP/iapp/iapp_retrieve_gdas_gfs.csh $
# $Id: iapp_retrieve_gdas_gfs.csh 2346 2015-02-05 20:35:32Z geoffc $
#

#-------------------------------------------------------------------------------
# SETUP AND CHECK ARGUMENTS
#-------------------------------------------------------------------------------

# If the local ancillary directory variable is not set, then default to 
#  current directory

if ( ! $?CSPP_EDR_ANC_CACHE_DIR ) then
   echo "Setting CSPP_EDR_ANC_CACHE_DIR as "${PWD}
   setenv CSPP_EDR_ANC_CACHE_DIR ${PWD}
endif

# If the remote ancillary directory variable is not set, then default to 
#  the JPSS ancillary data web site:
echo "(GPC) Setting JPSS_REMOTE_ANC_DIR..."
if ( ! $?JPSS_REMOTE_ANC_DIR ) then
  #setenv JPSS_REMOTE_ANC_DIR http://jpssdb.ssec.wisc.edu/ancillary
  setenv JPSS_REMOTE_ANC_DIR ftp://ftp.ssec.wisc.edu/pub/eosdb/ancillary
endif
echo "(GPC) Set JPSS_REMOTE_ANC_DIR as "${JPSS_REMOTE_ANC_DIR}

# Check for CSPP_HOME environment variable
#if (! ${?CSPP_HOME}) then
  #echo "Error: Environment variable CSPP_HOME is not set"
  #exit 1
#endif

# Check number of arguments
if ($#argv < 1 || $#argv > 2) then
  echo "Usage: iapp_retrieve_gdas_gfs.csh VIIRS_GMOD [search_flag]"
  echo "where"
  echo "VIIRS_GMOD is the VIIRS Geolocation HDF5 filename"
  echo "  search_flag - Optional:"
  echo "    1 - Search locally only, 0 (default) - Search local and remotely"
  exit 1
endif

# Echo command line
echo "(GPC) Echoing command line..."
echo
echo $0 $argv
echo "(GPC) Echoed command line..."


# Check that input files exist
#foreach FILE ($argv[1])
  #if (! -e $FILE) then
    #echo "Input file not found: "$FILE
    #exit 1
  #endif
#end

#-------------------------------------------------------------------------------
# EXTRACT ARGUMENTS
#-------------------------------------------------------------------------------


# Extract file names and directories
echo "(GPC) Extract file names and directories..."
set VIIRS_GEO = $argv[1]
set FILENAME=`basename $VIIRS_GEO`

if ($#argv == 2 ) then
  set search_flag = $argv[2]
  if ($search_flag != "0" && $search_flag != "1") then
    echo "Search flag must be set to either 0 or 1 " > /dev/stderr
    exit 1
  endif
else
  set search_flag = 0  
endif
echo "(GPC) Extracted file names and directories..."

echo "-------------------------------------------------------------------------"
echo "Begin Processing data file: $FILENAME at " `date`
echo "-------------------------------------------------------------------------"

#  Extract date and time from filename
# Set root of output file name (e.g. 't1.02001.1815')
set ROOT = $VIIRS_GEO:r
set ROOT = $ROOT:r
set ROOT = $ROOT:t

# Get year and date for ancillary data extraction
set YEAR     = `echo $VIIRS_GEO:t | cut -c12-15`
set MONTH    = `echo $VIIRS_GEO:t | cut -c16-17`
set DAY    = `echo $VIIRS_GEO:t | cut -c18-19`
set HOUR   = `echo $VIIRS_GEO:t | cut -c 22-23`
set MINUTE = `echo $VIIRS_GEO:t | cut -c 24-25`

# Get Julian Day of year for ancillary data scripts
set JDAY=`date --date="$YEAR-$MONTH-$DAY" "+%j"`

set DATE   =  ${YEAR}${JDAY}
set ITIME   = ${HOUR}${MINUTE}


#Strip leading zeros from day
set DAY=`echo $DAY | sed 's/^0//'`
if ($DAY < 1 || $DAY > 366) then
  echo "Invalid day of year: "$DATE
  exit 1
endif
#Strip leading zeros from time
set TIME=`echo $ITIME | sed 's/^0//'`

if (0 > $TIME || 2359 < $TIME ) then
#if ($TIME < 0 || $TIME > 2359) then
  echo "Invalid time: "$TIME
  exit 1
endif

echo "-------------------------------------------------------------------------"
echo "Processing data from $YEAR-$MONTH-$DAY and $ITIME UTC"
echo "-------------------------------------------------------------------------"

#-------------------------------------------------------------------------------
# GET GDAS OR GFS ANCILLARY FILES
#-------------------------------------------------------------------------------

echo
echo "(Getting GDAS or GFS ancillary data for $YEAR day $JDAY and time $TIME)"

# Get the correct first numerical weather prediction file
echo
set pre_time = `iapp_before_and_after_time.csh $DATE $TIME BACKWARD`
set forecast_date1=`echo $pre_time | cut -c 1-7`
set forecast_time1=`echo $pre_time | cut -c 8-11`
set GDAS1=`get_anc_iapp_gdas_gfs.csh $forecast_date1 $forecast_time1 $search_flag`
if ($GDAS1 == "") then
  echo 
  echo $0" ERROR: processing failed."
  echo "GDAS/GFS ancillary data could not be found for date "$DATE" and time "$TIME
  echo
  exit 1
else
  echo
  echo "GDAS/GFS file 1: "$GDAS1
endif

# Get the correct second numerical weather prediction file
echo
set post_time = `iapp_before_and_after_time.csh $DATE $TIME FORWARD`
set forecast_date2=`echo $post_time | cut -c 1-7`
set forecast_time2=`echo $post_time | cut -c 8-11`
set GDAS2=`get_anc_iapp_gdas_gfs.csh $forecast_date2 $forecast_time2 $search_flag`
if ($GDAS2 == "") then
  echo 
  echo $0" ERROR: processing failed."
  echo "GDAS/GFS ancillary data could not be found for date "$DATE" and time "$TIME
  echo
  exit 1
else
  echo
  echo "GDAS/GFS file 2: "$GDAS2
endif

# Get separate path and file names
set FILGDAS1 = `basename $GDAS1`
set FILGDAS2 = `basename $GDAS2`
set DIRGDAS1 = `dirname $GDAS1`
set DIRGDAS2 = `dirname $GDAS2`

#-------------------------------------------------------------------------------
# EXTRACT BINARY FIELDS FROM ANCILLARY FILES
#-------------------------------------------------------------------------------

#echo
#echo "(Extracting Fields from the GRIB2 ancillary data files)"
#echo

## extract binary fields from forecast files
#set GDAS1_BIN=${FILGDAS1}.bin
#set GDAS2_BIN=${FILGDAS2}.bin
#set prefix1=`echo $FILGDAS1 | cut -d. -f1`
#set prefix2=`echo $FILGDAS2 | cut -d. -f1`
#if ("$prefix1" == "gfs") then 
   #echo "extract_jpss_gfs_to_bin.csh $GDAS1 $GDAS1_BIN"
   #extract_jpss_gfs_to_bin.csh $GDAS1 $GDAS1_BIN
#else if ("$prefix1" == "gdas1") then
   #extract_jpss_gdas1_to_bin.csh $GDAS1 $GDAS1_BIN
   #echo "extract_jpss_gdas1_to_bin.csh $GDAS1 $GDAS1_BIN"
#else
   #echo "Problem with ancillary filename:  $GDAS1"
   #exit 1
#endif

#if ("$prefix2" == "gfs") then 
   #echo "extract_jpss_gfs_to_bin.csh $GDAS2 $GDAS2_BIN"
   #extract_jpss_gfs_to_bin.csh $GDAS2 $GDAS2_BIN
#else if ("$prefix2" == "gdas1") then
   #echo "extract_jpss_gdas1_to_bin.csh $GDAS2 $GDAS2_BIN"
   #extract_jpss_gdas1_to_bin.csh $GDAS2 $GDAS2_BIN
#else
   #echo "Problem with ancillary filename:  $GDAS2"
   #exit 1
#endif

#-------------------------------------------------------------------------------
# RUN THE SCIENCE ALGORITHM
#-------------------------------------------------------------------------------

#echo
##echo "(Running "$PRODUCT" algorithm)"
#echo "(Running PRODUCT algorithm)"
#echo


# Print finish message
echo
echo "-------------------------------------------------------------------------"
echo "End Product Processing at " `date`
echo "-------------------------------------------------------------------------"
echo
exit 0

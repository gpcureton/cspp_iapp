#!/bin/csh

#------------------------------------------------------------------------------
# Routine which figures out the 3 hour time period (00, 06, 12 or 18 UTC)
# closest in forward time to the given date and time or the 3 hour time period
# closest in backward time to the given date time.  Use the word "FORWARD" or 
# "BACKWARD" in the argument INCREMENT .  It passes the result back as an 
# echo of the date/time in the format of yyyydddhhmm .  
#
# This routine uses the unix "date" command.
#
# Written by Kathy Strabala   June 2011
#
#------------------------------------------------------------------------------

# Check number of arguments
if ($#argv != 3) then
  echo "Usage: jpss_before_and_after_time.csh date time increment"
  echo "where"
  echo "  date is the required date (yyyyddd)"
  echo "  time is the required time (hhmm)"
  echo "  increment is either "FORWARD" or "BACKWARD""
  exit 1
endif

# Get arguments
set date = $argv[1]
set time = $argv[2]
set INCREMENT = $argv[3]

#Fix problem with time = 0000 
if ($time > -1 && $time < 1 ) then
    set time = 1
endif

# Forward case
if ("${INCREMENT}" == "FORWARD") then

  # Must check for those cases when the pass time is equal to one of our
  #  3 hour time intervals. If so, then don't change the time.
  foreach time_step ( 0000 0300 0600 0900 1200 1500 1800 2100 )

    set timediff = `expr $time_step - $time`
    if ( $timediff == 0 ) then
       set result = $date$time
       echo $result
       exit 0
    else if ( $timediff > 0 && $timediff < 300 ) then
       set result = `expr $date$time_step + 1`
       echo $result
       exit 0
    endif
  end

  # For forward time only, we have to worry about the closest 3 hour forward
  #  time being a 00 hour forecast file for the next day.
  if ( $time > 2100 ) then
         
      set jday=`echo $date | cut -c5-7`
      set data_year=`echo $date | cut -c1-4`
      set file_date=`date --date="$data_year-01-01 + $jday days" "+%Y%j"`

      set result=${file_date}0000
      echo $result
      exit 0

  endif

endif

# Backward case
if ("${INCREMENT}" == "BACKWARD") then

  # Backward time is easier.  It is just where the difference between
  #  data time and analysis time is less than 3.

  # Must check for those cases when the pass time is equal to one of our
  #  3 hour time intervals. If so, then don't change the time.
  foreach time_step ( 0000 0300 0600 0900 1200 1500 1800 2100 )

    set timediff = `expr $time - $time_step`
    if ( $timediff == 0 ) then
       set result = $date$time
       echo $result
       exit 0
    else if ( $timediff > 0 && $timediff < 300 ) then
       set result = $date$time_step
       echo $result
       exit 0
    endif
  end

endif

# If we get here, the script was not able to find a date/time
echo "ERROR: Could not evaluate a suitable FORWARD or BACKWARD date/time"  > /dev/stderr

exit 1

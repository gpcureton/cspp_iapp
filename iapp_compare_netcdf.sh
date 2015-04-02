#!/bin/bash
### Verify CSPP IAPP test products with known products ###
#
# Copyright (C) 2015 Space Science and Engineering Center (SSEC),
#  University of Wisconsin-Madison.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#     kathy.strabala@ssec.wisc.edu

# Check arguments
if [ $# -ne 2 ]; then
  echo "Usage: iapp_compare_netcdf.sh verification_dir work_dir"
  exit 1
fi

# Get primary and secondary directory names
VERIFY_BASE=$1
WORK_DIR=$2

oops() {
    echo "OOPS: $*"
    echo "FAILURE"
    exit 1
}

if [ ! -d $VERIFY_BASE ]; then
    oops "Verification directory $WORK_DIR does not exist"
fi

if [ ! -d $WORK_DIR ]; then
    oops "Working directory $WORK_DIR does not exist"
fi

# Run tests for each test data directory in the base directory
BAD_COUNT=0
for VFILE in $VERIFY_BASE/*iapp.nc; do
    SHORT=$(basename $VERIFY_BAS/$VFILE | cut -d_ -f1-5)
    WFILE=`find $WORK_DIR -name "$SHORT*" -print`
    if [ ! -f $WFILE ]; then
        echo "ERROR: Could not find output file $WFILE"
        BAD_COUNT=$(($BAD_COUNT + 1))
        continue
    fi
    echo "Comparing Temperature_Retrieval array in $WFILE to validation file"
    $CSPP_IAPP_HOME/common/ShellB3/bin/python <<EOF
from netCDF4 import Dataset
import numpy
import sys

nc1_name  = "$VFILE"
nc2_name  = "$WFILE"
threshold = 1

nc1 = Dataset(nc1_name, "r")
nc2 = Dataset(nc2_name, "r")
image1_var = nc1.variables["Temperature_Retrieval"]
image2_var = nc2.variables["Temperature_Retrieval"]
image1_var.set_auto_maskandscale(False)
image2_var.set_auto_maskandscale(False)
image1_data = image1_var[:].astype(numpy.float)
image2_data = image2_var[:].astype(numpy.float)

if image1_data.shape != image2_data.shape:
    print "ERROR: Data shape for '$WFILE' is not the same as the valid '$VFILE'"
    sys.exit(1)

total_pixels = image1_data.shape[0] * image1_data.shape[1] * image1_data.shape[2]
equal_pixels = len(numpy.nonzero((image2_data - image1_data) < threshold)[0])
if equal_pixels != total_pixels:
    print "FAIL: %d pixels out of %d pixels are different" % (total_pixels-equal_pixels,total_pixels)
    sys.exit(2)
print "SUCCESS: %d pixels out of %d pixels are different" % (total_pixels-equal_pixels,total_pixels)

EOF
[ $? -eq 0 ] || BAD_COUNT=$(($BAD_COUNT + 1))
done

if [ $BAD_COUNT -ne 0 ]; then
    "$BAD_COUNT files were found to be unequal"
fi

# End of all tests
echo "All files passed"
echo "SUCCESS"


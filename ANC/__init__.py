#!/usr/bin/env python
# encoding: utf-8
"""
This module re-implements the ANC gridded ingest and granulation
in the Algorithm Development Package (ADL).

Created by Geoff Cureton on 2013-02-25.
Copyright (c) 2013 University of Wisconsin SSEC. All rights reserved.
"""

file_Date = '$Date: 2013-08-26 18:23:10 -0500 (Mon, 26 Aug 2013) $'
file_Revision = '$Revision: 1609 $'
file_Author = '$Author: geoffc $'
file_HeadURL = '$HeadURL: https://svn.ssec.wisc.edu/repos/jpss_adl/trunk/scripts/edr/ANC/__init__.py $'
file_Id = '$Id: __init__.py 1609 2013-08-26 23:23:10Z geoffc $'

__author__ = 'G.P. Cureton <geoff.cureton@ssec.wisc.edu>'
__version__ = '$Id: __init__.py 1609 2013-08-26 23:23:10Z geoffc $'
__docformat__ = 'Epytext'


#import ProCmnPhysConst
from Utils import retrieve_NCEP_grib_files
from Utils import transcode_NCEP_grib_files
from Utils import retrieve_METAR_files
from Utils import transcode_METAR_files

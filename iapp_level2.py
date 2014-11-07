#!/usr/bin/env python
# encoding: utf-8
"""
iapp_level2.py

Purpose: Run the IAPP package on level-1D files to generate level-2 files.

Input:
    * HIRS AAPP Level-1D file.
    * Static IGBP,LWM,NDVI files.
    * A work directory, typically, empty, in which to unpack the granules and 
      generate the output. If the work directory specified does not exist, it 
      will be created.

Output:
    * NetCDF file output from IAPP

Details:
    * 

Preconditions:
    * 

Optional:
    * 

Minimum commandline:

    python iapp_level2.py  --input_files=INPUTFILES --satellite=SATELLITE

where...

    INPUTFILES: The fully qualified path to the input files. May be a directory 
    or a file glob.


Created by Geoff Cureton <geoff.cureton@ssec.wisc.edu> on 2014-09-24.
Copyright (c) 2014-2014 University of Wisconsin Regents. All rights reserved.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

file_Date = '$Date$'
file_Revision = '$Revision$'
file_Author = '$Author$'
file_HeadURL = '$HeadURL$'
file_Id = '$Id$'

__author__ = 'Geoff Cureton <geoff.cureton@ssec.wisc.edu>'
__version__ = '$Id$'
__docformat__ = 'Epytext'


import os, sys, logging, traceback
from os import path,uname,environ
import string
import struct
import re
import uuid
import shlex, subprocess
from subprocess import CalledProcessError, call
from shutil import rmtree,copyfile,move
from glob import glob
from time import time,sleep
from datetime import datetime,timedelta

import numpy as np
from numpy import ma
import copy

import tables as pytables
from tables import exceptions as pyEx

from multiprocessing import Pool, Lock, Value, cpu_count

from adl_common import sh, env 
from adl_common import check_and_convert_path,check_existing_env_var
from adl_common import CSPP_RT_HOME, CSPP_RT_ANC_PATH, CSPP_RT_ANC_CACHE_DIR

from adl_common import IAPP_HOME

from ANC import retrieve_NCEP_grib_files, transcode_NCEP_grib_files
from ANC import retrieve_METAR_files, transcode_METAR_files

# every module should have a LOG object
sourcename= file_Id.split(" ")
LOG = logging.getLogger(sourcename[1])
from adl_common import configure_logging

###################################################
#                  Global Data                    #
###################################################

environ['TZ'] = 'UTC'
hexPat = '[\\dA-Fa-f]'

def _create_input_file_globs(inputFiles):
    '''
    Determine the correct input file path and globs
    '''
    input_path = path.abspath(inputFiles)
    if path.isdir(input_path) :
        input_dir = input_path
        input_files = None
    else :
        input_dir = path.dirname(input_path)
        input_files = path.basename(input_path)

    LOG.debug("input_path = %s" %(input_path))
    LOG.debug("input_dir = %s" %(input_dir))
    LOG.debug("input_files = %s" %(input_files))

    inputGlob = None

    charsToKill = string.ascii_letters + string.digits + "."

    if (input_files is None):
        # Input file glob is of form "/path/to/files"
        LOG.debug('Path1')
        inputGlob = '*.h5'

    elif path.isfile(input_path) :
        # Input file glob is of form "/path/to/files/GMTCO_npp_d_t_e_b_c_cspp_dev.h5" 
        LOG.debug('Path2')
        fileGlob = string.rstrip(string.lstrip(string.split(input_files,"b")[0],charsToKill),charsToKill)
        LOG.debug("fileGlob = %s" %(fileGlob))
        inputGlob = "*%s*.h5" %(fileGlob)
        LOG.debug("Initial inputGlob = %s" %(inputGlob))
        while (string.find(inputGlob,"**")!= -1): 
            inputGlob = string.replace(inputGlob,"**","*")
            LOG.debug("New inputGlob = %s" %(inputGlob))

    elif ("*" in input_files):
        # Input file glob is of form "/path/to/files/*"
        LOG.debug('Path3')
        fileGlob = string.rstrip(string.lstrip(string.split(input_files,"b")[0],charsToKill),charsToKill)
        inputGlob = "*%s*.h5" %(fileGlob)
        LOG.debug("Initial inputGlob = %s" %(inputGlob))
        while (string.find(inputGlob,"**")!= -1): 
            inputGlob = string.replace(inputGlob,"**","*")
            LOG.debug("New inputGlob = %s" %(inputGlob))

    return input_dir,inputGlob


    return requiredGeoShortname,requiredGeoPrefix


def _strReplace(fileName,oldString,newString):
    """
    Check fileName for occurences of oldString, if found fileName is opened and oldString is 
    replaced with newString.
    """
    fileChanged=0
    try :
        with open(fileName) as thefile:
            content = thefile.read()                 # read entire file into memory
            replacedText = content.replace(oldString, newString)
        if replacedText != content:
            LOG.debug('Replacing occurence of "%s" in %s with "%s"' % (oldString,path.basename(fileName),newString))
            with open(fileName, 'w') as thefile:
                thefile.write(replacedText)
            fileChanged=1
        return fileChanged
    except Exception, err :
        LOG.error("{}.".format(err))


def _convert_datetime(s):
    "converter which takes strings from ASC and converts to computable datetime objects"
    pt = s.rfind('.')
    micro_s = s[pt+1:]
    micro_s += '0'*(6-len(micro_s))
    #when = dt.datetime.strptime(s[:pt], '%Y-%m-%d %H:%M:%S').replace(microsecond = int(micro_s))
    when = datetime.strptime(s[:pt], '%Y-%m-%d %H:%M:%S').replace(microsecond = int(micro_s))
    return when

def _convert_isodatetime(s):
    "converter which takes strings from ASC and converts to computable datetime objects"
    pt = s.rfind('.')
    micro_s = s[pt+1:]
    micro_s += '0'*(6-len(micro_s))
    #when = dt.datetime.strptime(s[:pt], '%Y-%m-%d %H:%M:%S').replace(microsecond = int(micro_s))
    when = datetime.strptime(s[:pt], '%Y-%m-%dT%H:%M:%S').replace(microsecond = int(micro_s))
    return when


def _getURID() :
    '''
    Create a new URID to be used in making the asc filenames
    '''
    
    URID_dict = {}

    URID_timeObj = datetime.utcnow()
    
    creationDateStr = URID_timeObj.strftime("%Y-%m-%d %H:%M:%S.%f")
    creationDate_nousecStr = URID_timeObj.strftime("%Y-%m-%d %H:%M:%S.000000")
    
    tv_sec = int(URID_timeObj.strftime("%s"))
    tv_usec = int(URID_timeObj.strftime("%f"))
    hostId_ = uuid.getnode()
    thisAddress = id(URID_timeObj)
    
    l = tv_sec + tv_usec + hostId_ + thisAddress
    
    URID = '-'.join( ('{0:08x}'.format(tv_sec)[:8],
                      '{0:05x}'.format(tv_usec)[:5],
                      '{0:08x}'.format(hostId_)[:8],
                      '{0:08x}'.format(l)[:8]) )
    
    URID_dict['creationDateStr'] = creationDateStr
    URID_dict['creationDate_nousecStr'] = creationDate_nousecStr
    URID_dict['tv_sec'] = tv_sec
    URID_dict['tv_usec'] = tv_usec
    URID_dict['hostId_'] = hostId_
    URID_dict['thisAddress'] = thisAddress
    URID_dict['URID'] = URID
    
    return URID_dict


def _fuse(*exps):
    "fuse regular expressions together into a single or-expression"
    return '|'.join(r'(?:%s)' % x for x in exps)


def __cleanup(work_dir, files_to_remove, dirs_to_remove):
    '''
    Remove runfiles and the executable logfiles.
    '''
    # Remove files
    for filename in files_to_remove:
        fullFileName = path.join(work_dir,filename)
        try :
            if path.isfile(fullFileName) and not path.islink(fullFileName):
                LOG.debug('Removing file {}'.format(fullFileName))
                os.unlink(fullFileName)

            if path.islink(fullFileName):
                LOG.debug('Removing link {}'.format(fullFileName))
                os.unlink(fullFileName)
        except Exception, err:
            LOG.warn( "{}".format(str(err)))

    # Remove log directory
    LOG.debug("Removing other directories ...")
    for dirname in dirs_to_remove:
        fullDirName = path.join(work_dir,dirname)
        LOG.debug('Removing {}'.format(fullDirName))
        try :
            rmtree(fullDirName, ignore_errors=False)
        except Exception, err:
            LOG.warn( "{}".format(str(err)))


class Level1D():
    '''
    This class opens the supplied Level-1D file and reads the header, returning
    an object populated with the header data. The corresponding Fortran90 struct
    in IAPP can be found in HIRS_1D_record.f90
    '''

    def __init__(self,file_name):

        self.input_file = path.abspath(file_name)

        self.header_field_comments = {}

        self.header_field_comments['Dataset_Creation_Site'] = "1D dataset creation site ID"
        self.header_field_comments['Filler_1']              = "filler"
        self.header_field_comments['Creation_1BSite']       = "creation site for original 1B data"
        self.header_field_comments['Filler_2']              = "filler"

        self.header_field_comments['Header_Version_Number']    = "level 1d format version number"
        self.header_field_comments['Header_Version_Year']      = "level 1d format version year"
        self.header_field_comments['Header_Version_DOY']       = "level 1d format version day of year"
        self.header_field_comments['Number_of_Header_Records'] = "count of header records in this data set"
        self.header_field_comments['Satellite_ID']             = "satellite id (e.g. 14 for NOAA-14)"
        self.header_field_comments['Inst_Grid_Code']           = "code for instrument grid (5=HIRS; 6=MSU; 10=AMSU-A; 11=MHS)"
        self.header_field_comments['Satellite_Altitude']       = "nominal satellite altitude, km*10"
        self.header_field_comments['Nominal_Orbit_Period']     = "nominal orbit period (seconds)"
        self.header_field_comments['Start_Orbit_Number']       = "orbit number (at start of dataset)"
        self.header_field_comments['Start_Data_Set_Year']      = "start of data set year"
        self.header_field_comments['Start_Data_Set_DOY']       = "start of data set day of the year"
        self.header_field_comments['Start_Data_Set_UTC_Time']  = "start of data set UTC time of day (ms)"
        self.header_field_comments['End_Orbit_Number']         = "orbit number (at end of dataset)"
        self.header_field_comments['End_Data_Set_Year']        = "end of data set year"
        self.header_field_comments['End_Data_Set_DOY']         = "end of data set day of the year"
        self.header_field_comments['End_Data_Set_UTC_Time']    = "end of data set UTC time of day (ms)"
        self.header_field_comments['Number_of_Scanlines']      = "count of scan lines in this data set"
        self.header_field_comments['Missing_Scanlines']        = "count of missing scan lines"
        self.header_field_comments['ATOVPP_Version_Number']    = "ATOVPP version number (test vns = 9000+)"
        self.header_field_comments['Instruments']              = "instruments present (bit0=HIRS, bit1=MSU, bit3=AMSU-A, bit4=MHS, bit5=AVHRR)"

        self.header_field_size = {}

        self.header_field_size['Dataset_Creation_Site'] = 3
        self.header_field_size['Filler_1']              = 1
        self.header_field_size['Creation_1BSite']       = 3
        self.header_field_size['Filler_2']              = 1

        self.header_field_size['Header_Version_Number']    = 4
        self.header_field_size['Header_Version_Year']      = 4
        self.header_field_size['Header_Version_DOY']       = 4
        self.header_field_size['Number_of_Header_Records'] = 4
        self.header_field_size['Satellite_ID']             = 4
        self.header_field_size['Inst_Grid_Code']           = 4
        self.header_field_size['Satellite_Altitude']       = 4
        self.header_field_size['Nominal_Orbit_Period']     = 4
        self.header_field_size['Start_Orbit_Number']       = 4
        self.header_field_size['Start_Data_Set_Year']      = 4
        self.header_field_size['Start_Data_Set_DOY']       = 4
        self.header_field_size['Start_Data_Set_UTC_Time']  = 4
        self.header_field_size['End_Orbit_Number']         = 4
        self.header_field_size['End_Data_Set_Year']        = 4
        self.header_field_size['End_Data_Set_DOY']         = 4
        self.header_field_size['End_Data_Set_UTC_Time']    = 4
        self.header_field_size['Number_of_Scanlines']      = 4
        self.header_field_size['Missing_Scanlines']        = 4
        self.header_field_size['ATOVPP_Version_Number']    = 4
        self.header_field_size['Instruments']              = 4

        # Open the data file for reading
        self.file_obj = open(file_name,'rb')

        self.header_field_data = {}

        # Read the character typed datasets and save to data dictionary.
        datasets=  ['Dataset_Creation_Site','Filler_1','Creation_1BSite','Filler_2']
        self.read_header(datasets,None)

        # Read the long integer typed datasets and save to data dictionary.
        datasets = ['Header_Version_Number', 'Header_Version_Year', 'Header_Version_DOY', \
                'Number_of_Header_Records', 'Satellite_ID', 'Inst_Grid_Code', \
                'Satellite_Altitude', 'Nominal_Orbit_Period', 'Start_Orbit_Number', \
                'Start_Data_Set_Year', 'Start_Data_Set_DOY', 'Start_Data_Set_UTC_Time', \
                'End_Orbit_Number', 'End_Data_Set_Year', 'End_Data_Set_DOY', \
                'End_Data_Set_UTC_Time', 'Number_of_Scanlines', 'Missing_Scanlines', \
                   'ATOVPP_Version_Number', 'Instruments']
        self.read_header(datasets,'i')

        # Close the data file
        self.file_obj.close()

        # Set the pass start, mid and end datetime objects from the timing 
        # information in the data dictionary.
        self.set_datetime()


    def read_header(self,datasets,format_str):
        ''' Sequentially reads binary chunks from the data file.'''

        for dataset in datasets:
            data = self.file_obj.read(self.header_field_size[dataset])

            # Only unpack non-char data.
            if format_str is not None:
                data = struct.unpack(format_str, data)[0]
            
            self.header_field_data[dataset] = data
            LOG.debug("{} : {}".format(self.header_field_comments[dataset],
                    self.header_field_data[dataset]))


    def set_datetime(self):
        '''Use the header time info to set several datetime objects.'''

        start_year = self.header_field_data['Start_Data_Set_Year']
        start_day_of_year = self.header_field_data['Start_Data_Set_DOY']
        start_UTC_time_ms = self.header_field_data['Start_Data_Set_UTC_Time']

        LOG.debug("Start Dataset year: {}".format(start_year))
        LOG.debug("Start Dataset day_of_year: {}".format(start_day_of_year))
        LOG.debug("Start Dataset UTC_time_ms: {}".format(start_UTC_time_ms))

        end_year = self.header_field_data['End_Data_Set_Year']
        end_day_of_year = self.header_field_data['End_Data_Set_DOY']
        end_UTC_time_ms = self.header_field_data['End_Data_Set_UTC_Time']

        LOG.debug("End Dataset year: {}".format(end_year))
        LOG.debug("End Dataset day_of_year: {}".format(end_day_of_year))
        LOG.debug("End Dataset UTC_time_ms: {}".format(end_UTC_time_ms))

        time_string = "{}-{}".format(start_year,start_day_of_year)
        timeObj_start = datetime.strptime(time_string, '%Y-%j')
        timeObj_start = timeObj_start + timedelta(milliseconds=start_UTC_time_ms)
        pass_start_str = timeObj_start.strftime("%Y-%m-%d %H:%M:%S.%f")

        time_string = "{}-{}".format(end_year,end_day_of_year)
        timeObj_end = datetime.strptime(time_string, '%Y-%j')
        timeObj_end = timeObj_end + timedelta(milliseconds=end_UTC_time_ms)
        pass_end_str = timeObj_end.strftime("%Y-%m-%d %H:%M:%S.%f")

        pass_length = (timeObj_end - timeObj_start).seconds
        timeObj_mid = timeObj_start + timedelta(seconds=pass_length/2.)
        pass_mid_str = timeObj_mid.strftime("%Y-%m-%d %H:%M:%S.%f")

        LOG.info("Pass start time: {}".format(pass_start_str))
        LOG.info("Pass mid time:   {}".format(pass_mid_str))
        LOG.info("Pass end time:   {}".format(pass_end_str))
        LOG.info("Pass length: {} seconds".format(pass_length))

        self.pass_start_str = pass_start_str
        self.pass_mid_str = pass_mid_str
        self.pass_end_str = pass_end_str

        self.timeObj_start = timeObj_start
        self.timeObj_mid = timeObj_mid
        self.timeObj_end = timeObj_end


runfile_template="""{}
{}
{}
{}
{}
{}
{}
{}
{}
{}
"""

def generate_iapp_runfile(work_dir,**template_dict):
    "generate XML files for VIIRS Masks EDR granule generation"
    runfile_name = path.join(work_dir,'iapp.filenames')

    if path.exists(runfile_name):
        os.unlink(runfile_name)

    LOG.debug('Writing IAPP runfile {}'.format(runfile_name))
    runfile_obj = file(runfile_name, 'w')

    runfile_obj.write(
            runfile_template.format(
                    template_dict['level1d_file'],
                    template_dict['topography_file'],
                    template_dict['gdas_gfs_netcdf_file'],
                    template_dict['metar_file'],
                    template_dict['radiosonde_file'],
                    template_dict['retrieval_method'],
                    template_dict['print_option'],
                    template_dict['satellite_name'],
                    template_dict['instrument_combo'],
                    template_dict['retrieval_bounds']
                )
            )

    runfile_obj.close()


def check_exe(exeName):
    ''' Check that a required executable is in the path...'''    
    try:
        retVal = sh(['which',exeName])
        LOG.info("{} is in the PATH...".format(exeName))
    except CalledProcessError:
        LOG.error("Required executable {} is not in the path or is not installed, aborting."
                .format(exeName))
        sys.exit(1)


def link_run_files(files_to_link,work_dir):
    '''Link various remote files into work_dir'''

    for file_key in files_to_link.keys():

        if files_to_link[file_key] == "":

            files_to_link[file_key] = ""

        else:
            remote_file = path.abspath(files_to_link[file_key])
            local_file = path.basename(remote_file)

            LOG.debug("Remote {} file: {}".format(file_key,remote_file))
            LOG.debug("Local  {} file: {}".format(file_key,local_file))

            if not path.exists(local_file):
                LOG.debug("Creating the link {} -> {}"
                        .format(local_file,remote_file))
                os.symlink(remote_file, local_file)
            else:
                LOG.debug('{} already exists; continuing'
                        .format(local_file))

            files_to_link[file_key] = local_file


    return files_to_link


def link_iapp_coeffs(work_dir):
    '''Link the IAPP coefficients dir into the dir above the work dir'''

    IAPP_COEFFS_DIR = path.abspath(path.join(IAPP_HOME,'iapp','iapp_coefs'))
    LOCAL_COEFFS_DIR = path.abspath(path.join(path.dirname(work_dir),'iapp_coefs'))
    LOG.debug("Remote IAPP coeffs directory: {}".format(IAPP_COEFFS_DIR))
    LOG.debug("Local IAPP coeffs directory: {}".format(LOCAL_COEFFS_DIR))

    if not path.exists(LOCAL_COEFFS_DIR):
        LOG.debug("Creating the link {} -> {}"
                .format(LOCAL_COEFFS_DIR,IAPP_COEFFS_DIR))
        os.symlink(IAPP_COEFFS_DIR, LOCAL_COEFFS_DIR)
    else:
        LOG.debug('{} already exists; continuing'
                .format(LOCAL_COEFFS_DIR))


def create_retrieval_netcdf_template(work_dir):
    '''Create the template NetCDF file uwretrievals.nc'''

    NCGEN_PATH=path.abspath(path.join(CSPP_RT_HOME,'common','ShellB3','bin'))
    CDL_FILES_PATH=path.abspath(path.join(IAPP_HOME,'iapp','cdlfiles'))

    # Check that we have access to the NetCDF generation exe...
    scriptPath = "{}/ncgen".format(NCGEN_PATH)
    if not path.exists(scriptPath):
        LOG.error('{} can not be found, aborting.'.format(scriptPath))
        sys.exit(1)

    netcdf_template_file = '{}/uwretrievals.nc'.format(work_dir)

    # Remove an existing template file...
    if path.exists(netcdf_template_file):
        LOG.debug('Removing existing NetCDF retrieval template file {}'
                .format(netcdf_template_file))
        os.unlink(netcdf_template_file)

    # Construct the command line args to ncgen
    script_args = '{}/uwretrievals.cdl -o {}'.format(
            CDL_FILES_PATH,
            netcdf_template_file
            )

    try :
        # Call the NetCDF template generation exe, writing the logging output to a file
        LOG.info('Creating NetCDF template file {} ...'.format(netcdf_template_file))
        cmdStr = '{} {}'.format(scriptPath,script_args)
        LOG.debug('\t{}'.format(cmdStr))
        args = shlex.split(cmdStr)

        procRetVal = 0
        procObj = subprocess.Popen(args,
                env=env(
                    CSPP_RT_HOME=CSPP_RT_HOME,
                    NCGEN_PATH=NCGEN_PATH
                    ),
                bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode

        procOutput = procObj.stdout.readlines()

        for lines in procOutput:
            LOG.debug(lines)

        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Creating NetCDF template file {} failed, aborting...'
                    .format(netcdf_template_file))
            sys.exit(procRetVal)

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())


    LOG.info('New NetCDF retrieval template file successfully created: {}'
            .format(netcdf_template_file))


def run_iapp_exe(options,Level1D_obj,work_dir,log_dir):
    '''Run the IAPP executable'''

    IAPP_EXE_PATH=path.abspath(path.join(IAPP_HOME,'iapp','bin'))


    # Check that we have access to the IAPP main exe...
    scriptPath = "{}/iapp_main".format(IAPP_EXE_PATH)
    if not path.exists(scriptPath):
        LOG.error('{} can not be found, aborting.'.format(scriptPath))
        sys.exit(1)

    netcdf_template_file = '{}/uwretrievals.nc'.format(work_dir)
    if not path.exists(netcdf_template_file):
        LOG.error('{} can not be found, aborting.'.format(netcdf_template_file))
        sys.exit(1)

    # Set up the logging
    d = datetime.now()
    timestamp = d.isoformat()
    logname= "iapp_main."+timestamp+".log"
    logpath= path.join(log_dir, logname )
    logfile_obj = open(logpath,'w')

    try :
        # Call the transcoding script, writing the logging output to a file
        LOG.info('Populating NetCDF template file {} ...'.format(netcdf_template_file))
        cmdStr = '{}'.format(scriptPath)
        LOG.debug('{}'.format(cmdStr))
        args = shlex.split(cmdStr)

        procRetVal = 0
        procObj = subprocess.Popen(args,
                env=env(
                    CSPP_RT_HOME=CSPP_RT_HOME,
                    IAPP_EXE_PATH=IAPP_EXE_PATH
                    ),
                bufsize=0, stdout=logfile_obj, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode

        logfile_obj.close()

        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Running IAPP main failed, aborting...'
                    .format(netcdf_template_file))
            sys.exit(procRetVal)

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())


    LOG.info('IAPP completed successfully created: {}'
            .format(netcdf_template_file))

    # Rename the output NetCDF file
    timeObj = Level1D_obj.timeObj_start
    dateStamp = timeObj.strftime("%Y%m%d")
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    deciSeconds = int(round(float(timeObj.microsecond)/100000.))
    deciSeconds = repr(0 if deciSeconds > 9 else deciSeconds)
    startTimeStamp = "%s%s" % (timeObj.strftime("%H%M%S"),deciSeconds)

    timeObj = Level1D_obj.timeObj_end
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    deciSeconds = int(round(float(timeObj.microsecond)/100000.))
    deciSeconds = repr(0 if deciSeconds > 9 else deciSeconds)
    endTimeStamp = "%s%s" % (timeObj.strftime("%H%M%S"),deciSeconds)

    timeObj = datetime.utcnow()
    creationTimeStamp = timeObj.strftime("%Y%m%d%H%M%S%f")

    iapp_retrieval_netcdf = "{}_L2_d{}_t{}_e{}_c{}_iapp.nc".format(
            options.satellite,
            dateStamp,
            startTimeStamp,
            endTimeStamp,
            creationTimeStamp)


    LOG.info('Moving {} to {}...'.format(
        netcdf_template_file,iapp_retrieval_netcdf
        ))
    move(netcdf_template_file,iapp_retrieval_netcdf)

    return iapp_retrieval_netcdf


def run_iapp_exe_dummy(options,Level1D_obj,work_dir,log_dir):
    '''Run the IAPP executable'''

    IAPP_EXE_PATH=path.abspath(path.join(IAPP_HOME,'iapp','bin'))

    netcdf_template_file = '{}/uwretrievals.nc'.format(work_dir)
    if not path.exists(netcdf_template_file):
        LOG.error('{} can not be found, aborting.'.format(netcdf_template_file))
        sys.exit(1)

    # Set up the logging
    d = datetime.now()
    timestamp = d.isoformat()
    logname= "iapp_main."+timestamp+".log"
    logpath= path.join(log_dir, logname )
    logfile_obj = open(logpath,'w')

    try :
        # Call the transcoding script, writing the logging output to a file
        LOG.info('Populating NetCDF template file {} ...'.format(netcdf_template_file))
        sleep(2)

        logfile_obj.close()

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())


    LOG.info('IAPP completed successfully created: {}'
            .format(netcdf_template_file))

    # Rename the output NetCDF file
    timeObj = Level1D_obj.timeObj_start
    dateStamp = timeObj.strftime("%Y%m%d")
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    deciSeconds = int(round(float(timeObj.microsecond)/100000.))
    deciSeconds = repr(0 if deciSeconds > 9 else deciSeconds)
    startTimeStamp = "%s%s" % (timeObj.strftime("%H%M%S"),deciSeconds)

    timeObj = Level1D_obj.timeObj_end
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    deciSeconds = int(round(float(timeObj.microsecond)/100000.))
    deciSeconds = repr(0 if deciSeconds > 9 else deciSeconds)
    endTimeStamp = "%s%s" % (timeObj.strftime("%H%M%S"),deciSeconds)

    timeObj = datetime.utcnow()
    creationTimeStamp = timeObj.strftime("%Y%m%d%H%M%S%f")

    iapp_retrieval_netcdf = "{}_L2_d{}_t{}_e{}_c{}_dummy.nc".format(
            options.satellite,
            dateStamp,
            startTimeStamp,
            endTimeStamp,
            creationTimeStamp)


    LOG.debug('Moving {} to {}...'.format(
        netcdf_template_file,iapp_retrieval_netcdf
        ))
    move(netcdf_template_file,iapp_retrieval_netcdf)

    return iapp_retrieval_netcdf

def _argparse():
    '''
    Method to encapsulate the option parsing and various setup tasks.
    '''

    import argparse

    satelliteChoices = ['noaa18','noaa19','metopa','metopb']
    instrumentChoices = {1:'(HIRS + AMSU-A)',2:'(AMSU-A only)',
            3:'(AMSU-A & MHS only)',4:'(HIRS, AMSU-A & MHS)'}
    retrievalMethodChoices = {0:'fixed',1:'dynamic'}

    defaults = {'work_dir':'.',
                'topography_file':'topography.nc',
                'forecast_model_file':None,
                'surface_obsv_file':None,
                'radiosonde_data_file':None,
                'retrieval_method':1,
                'print_retrieval':False,
                'print_l1d_header':False,
                'instrument_combo':4,
                'lower_latitude':0.,
                'upper_latitude':0.,
                'left_longitude':0.,
                'right_longitude':0.,
                'cspp_debug':False
                }

    description = '''Run the IAPP package on level-1D files to generate level-2 files.'''
    usage = "usage: %prog [mandatory args] [options]"
    version = __version__

    parser = argparse.ArgumentParser(
                                     #usage=usage,
                                     #version=version,
                                     description=description
                                     )

    # Mandatory arguments

    parser.add_argument('-i','--input_files',
                      action="store",
                      dest="inputFiles",
                      type=str,
                      required=True,
                      help='''The fully qualified path to the input files. May be
                            a directory or a file glob.'''
                      )

    parser.add_argument('--satellite',
                      action="store",
                      dest="satellite",
                      type=str,
                      required=True,
                      choices=satelliteChoices,
                      help='''The satellite name.\n\n
                              Possible values are...
                              {}.
                           '''.format(satelliteChoices.__str__()[1:-1])
                      )

    # Optional arguments 

    parser.add_argument('-w','--work_directory',
                      action="store",
                      dest="work_dir",
                      type=str,
                      default=defaults['work_dir'],
                      help='''The directory which all activity will occur in, 
                      defaults to the current directory. 
                      [default: {}]'''.format(defaults['work_dir'])
                      )
    
    parser.add_argument('-t','--topography_file',
                      action="store",
                      dest="topography_file",
                      type=str,
                      default=defaults['topography_file'],
                      help='''The topography file. 
                      [default: {}]'''.format(defaults['topography_file'])
                      )
    
    parser.add_argument('-f','--forecast_file',
                      action="store",
                      dest="forecast_model_file",
                      type=str,
                      default=defaults['forecast_model_file'],
                      help='''The GDAS/GFS forecast/analysis file (NetCDF format). 
                      [default: {}]'''.format(defaults['forecast_model_file'])
                      )
    
    parser.add_argument('-r','--radiosonde_file',
                      action="store",
                      dest="radiosonde_data_file",
                      type=str,
                      default=defaults['radiosonde_data_file'],
                      help='''The radiosonde file. 
                      [default: {}]'''.format(defaults['radiosonde_data_file'])
                      )
    
    parser.add_argument('-s','--surface_obs_file',
                      action="store",
                      dest="surface_obsv_file",
                      type=str,
                      default=defaults['surface_obsv_file'],
                      help='''The METAR surface observation file (NetCDF format). 
                      [default: {}]'''.format(defaults['surface_obsv_file'])
                      )
    
    parser.add_argument('--instrument_combo',
                      action="store",
                      dest="instrument_combo",
                      default=defaults['instrument_combo'],
                      type=int,
                      choices=instrumentChoices.keys(),
                      help='''Instrument combination. 
                      [default: {}]'''.format(defaults['instrument_combo'])
                      )

    parser.add_argument('--retrieval_method',
                      action="store",
                      dest="retrieval_method",
                      default=defaults['retrieval_method'],
                      type=int,
                      choices=retrievalMethodChoices.keys(),
                      help='''Retrieval method. 
                      [default: {}]'''.format(defaults['retrieval_method'])
                      )

    parser.add_argument('--lower_lat',
                      action="store",
                      dest="lower_latitude",
                      default=defaults['lower_latitude'],
                      type=float,
                      help='''Lower latitude for retrieval. 
                      [default: {}]'''.format(defaults['lower_latitude'])
                      )

    parser.add_argument('--upper_lat',
                      action="store",
                      dest="upper_latitude",
                      default=defaults['upper_latitude'],
                      type=float,
                      help='''Upper latitude for retrieval. 
                      [default: {}]'''.format(defaults['upper_latitude'])
                      )

    parser.add_argument('--left_lon',
                      action="store",
                      dest="left_longitude",
                      default=defaults['left_longitude'],
                      type=float,
                      help='''Left longitude for retrieval. 
                      [default: {}]'''.format(defaults['left_longitude'])
                      )

    parser.add_argument('--right_lon',
                      action="store",
                      dest="right_longitude",
                      default=defaults['right_longitude'],
                      type=float,
                      help='''Right longitude for retrieval. 
                      [default: {}]'''.format(defaults['right_longitude'])
                      )

    parser.add_argument('--print_retrieval',
                      action="store_true",
                      dest="print_retrieval",
                      default=defaults['print_retrieval'],
                      help='''Print the running output of the IAPP retrieval. 
                      [default: {}]'''.format(defaults['print_retrieval'])
                      )

    parser.add_argument('--print_l1d_header',
                      action="store_true",
                      dest="print_l1d_header",
                      default=defaults['print_l1d_header'],
                      help='''Print the level 1D header, and exit. 
                      [default: {}]'''.format(defaults['print_l1d_header'])
                      )

    parser.add_argument('--debug',
                      action="store_true",
                      dest="cspp_debug",
                      default=defaults['cspp_debug'],
                      help='''Enable debug mode and avoid cleaning 
                      workspace. 
                      [default: {}]'''.format(defaults['cspp_debug'])
                      )

    parser.add_argument('-v', '--verbose',
                      dest='verbosity',
                      action="count",
                      default=0,
                      help='''Each occurrence increases 
                      verbosity 1 level from INFO: -v=DEBUG'''
                      )

    #parser.add_argument('-V','--version',
                      #action='version',
                      #version='''{}\n
                                 #%(prog)s (myprog version 0.1)'''.format(version)
                      ##version='''%(prog)s (myprog version 0.1)'''
                      #)

    args = parser.parse_args()


    # Set the work directory
    work_dir = check_and_convert_path("WORK_DIR",args.work_dir)
    LOG.debug('Setting the work directory to %r' % (work_dir))

    # Set up the logging
    d = datetime.now()
    timestamp = d.isoformat()
    logname= "iapp_level2."+timestamp+".log"
    logfile= path.join(work_dir, logname )

    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbosity,3)]
    configure_logging(level,FILE=logfile)
    
    # create work directory
    if not path.isdir(work_dir):
        LOG.info('creating directory %s' % (work_dir))
        os.makedirs(work_dir)
        os.makedirs(path.join(work_dir,'run'))
    log_dir = path.join(work_dir, 'log')
    if not path.isdir(log_dir):
        LOG.debug('creating directory %s' % (log_dir))
        os.makedirs(log_dir)

    return args,work_dir ,log_dir



def main():

    options,work_dir,log_dir = _argparse()

    LOG.info("Starting CSPP IAPP ...")

    # Expand any user specifiers in the various paths
    LOG.debug("CSPP_RT_HOME:          {}".format(CSPP_RT_HOME))
    LOG.debug("CSPP_RT_ANC_PATH:      {}".format(CSPP_RT_ANC_PATH))
    LOG.debug("CSPP_RT_ANC_CACHE_DIR: {}".format(CSPP_RT_ANC_CACHE_DIR))

    # Parse the level 1D file header
    Level1D_obj = Level1D(options.inputFiles)

    if options.print_l1d_header:
        return 0

    # Specify the GRIB1 GDAS/GFS ancillary file
    if options.forecast_model_file is None:

        # Retrieve the required GRIB1 GDAS/GFS ancillary data...
        gribFiles = retrieve_NCEP_grib_files(Level1D_obj)
        LOG.info('Retrieved GFS files: {}'.format(gribFiles))

        # Transcode GRIB1 GDAS/GFS ancillary data to NetCDF
        grib_netcdf_file = transcode_NCEP_grib_files(gribFiles[0],work_dir,log_dir)
        LOG.info('Transcoded GDAS/GFS NetCDF file: {}'.format(grib_netcdf_file))

    else:
        grib_netcdf_file = options.forecast_model_file

    GRIB_FILE_PATH=path.abspath(path.dirname(grib_netcdf_file))
    LOG.debug('GRIB_FILE_PATH : {}'.format(GRIB_FILE_PATH))


    # Specify the METAR surface observation file
    if options.surface_obsv_file is None:

        # Retrieve the METAR Surface Observation ancillary data...
        metarFiles = retrieve_METAR_files(Level1D_obj,GRIB_FILE_PATH)
        LOG.info('Retrieved METAR files: {}'.format(metarFiles))

        # Transcode METAR ancillary data to NetCDF
        metar_netcdf_file = transcode_METAR_files(metarFiles[0],work_dir,log_dir)
        LOG.info('Transcoded METAR NetCDF file: {}'.format(metar_netcdf_file))

    else:
        metar_netcdf_file = options.surface_obsv_file


    # Set up some path variables
    LOG.info('VENDOR Location: {}'.format(IAPP_HOME))
    NETCDF_FILES_PATH=path.abspath(path.join(IAPP_HOME,'iapp','netcdf_files'))
    LOG.debug('NETCDF_FILES_PATH : {}'.format(NETCDF_FILES_PATH))

    # Create a list of files to link into the work directory, and link them...
    files_to_link = {
            'gdas_gfs_netcdf_file' : grib_netcdf_file, 
            'metar_file' : metar_netcdf_file,
            'topography_file' : path.join(NETCDF_FILES_PATH,'topography.nc'),
            'level1d_file' : options.inputFiles
            }
    linked_files = link_run_files(files_to_link, work_dir)

    # Create the runfile
    template_dict = {}
    template_dict['level1d_file'] = linked_files['level1d_file']
    template_dict['topography_file'] = linked_files['topography_file']
    template_dict['gdas_gfs_netcdf_file'] = linked_files['gdas_gfs_netcdf_file']
    template_dict['metar_file'] = linked_files['metar_file']
    template_dict['radiosonde_file'] = ''
    template_dict['retrieval_method'] = options.retrieval_method
    template_dict['print_option'] = 1 if options.print_retrieval else 0
    template_dict['satellite_name'] = options.satellite
    template_dict['instrument_combo'] = options.instrument_combo
    template_dict['retrieval_bounds'] = " {:1.0f}. {:1.0f}. {:1.0f}. {:1.0f}.".format(
            options.lower_latitude,options.upper_latitude,
            options.left_longitude,options.right_longitude)

    generate_iapp_runfile(work_dir,**template_dict)

    # Generate template netcdf retrieval file
    create_retrieval_netcdf_template(work_dir)

    # Create a link to the IAPP coefficient dir
    link_iapp_coeffs(work_dir)

    # Run the IAPP executable
    t1 = time()

    #iapp_retrieval_netcdf = run_iapp_exe_dummy(options,Level1D_obj,work_dir,log_dir)
    iapp_retrieval_netcdf = run_iapp_exe(options,Level1D_obj,work_dir,log_dir)
    
    t2 = time()
    LOG.info("iapp_main ran in {} seconds.".format(t2-t1))

    # General Cleanup...
    if not options.cspp_debug:
        files_to_remove = linked_files.values() + ['iapp.filenames']
        __cleanup(work_dir,files_to_remove,[log_dir])

    # TODO: Work out a sensible return code scheme.

    #if rc == 0 and not options.cspp_debug:
    #try :
        #return rc
    #except :
        #return 0

    return 0

if __name__=='__main__':
    sys.exit(main())  

#!/usr/bin/env python
# encoding: utf-8
"""
Utils.py

Various methods that are used by other methods in the ANC module.

Created by Geoff Cureton on 2013-03-04.
Copyright (c) 2013 University of Wisconsin SSEC. All rights reserved.
"""

file_Date = '$Date: 2014-07-11 20:12:29 -0500 (Fri, 11 Jul 2014) $'
file_Revision = '$Revision: 2184 $'
file_Author = '$Author: geoffc $'
file_HeadURL = '$HeadURL: https://svn.ssec.wisc.edu/repos/jpss_adl/trunk/scripts/edr/ANC/Utils.py $'
file_Id = '$Id: Utils.py 2184 2014-07-12 01:12:29Z geoffc $'

__author__ = 'G.P. Cureton <geoff.cureton@ssec.wisc.edu>'
__version__ = '$Id: Utils.py 2184 2014-07-12 01:12:29Z geoffc $'
__docformat__ = 'Epytext'

import os, sys, logging, traceback
from os import path,uname,environ
import string
import uuid
from datetime import datetime,timedelta

import numpy as np
from numpy import ma

import shlex, subprocess
from subprocess import CalledProcessError, call
from shutil import rmtree,copyfile,move
from glob import glob

import pygrib

from iapp_utils import sh, env
from iapp_utils import CSPP_RT_HOME, CSPP_RT_ANC_PATH, \
    CSPP_RT_ANC_CACHE_DIR, COMMON_LOG_CHECK_TABLE, env, JPSS_REMOTE_ANC_DIR
    
from iapp_utils import IAPP_HOME

# Plotting stuff
import matplotlib
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure

matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# This must come *after* the backend is specified.
import matplotlib.pyplot as ppl

# every module should have a LOG object
try :
    sourcename= file_Id.split(" ")
    LOG = logging.getLogger(sourcename[1])
except :
    LOG = logging.getLogger('Utils')


def getURID() :
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


def getAscLine(fileObj,searchString):
    ''' Parses a file and searches for a string in each line, returning 
        the line if the string is found.'''

    dataStr = ''
    try :
        while True :
            line = fileObj.readline()

            if searchString in line : 
                dataStr = "%s" % (string.replace(line,'\n',''));
                break

        fileObj.seek(0)

    except Exception, err:
        LOG.error('Exception: %r' % (err))
        LOG.debug(traceback.format_exc())
        fileObj.close()

    return dataStr


def getAscStructs(fileObj,searchString,linesOfContext):
    ''' Parses a file and searches for a string in each line, returning 
        the line (and a given number of lines of context) if the string 
        is found.'''

    dataList = []
    data_count = 0
    dataFound = False

    try :
        while True :
            line = fileObj.readline()

            if searchString in line : 
                dataFound = True

            if dataFound :
                dataStr = "%s" % (string.replace(line,'\n',''));
                dataList.append(dataStr)
                data_count += 1
            else :
                pass

            if (data_count == linesOfContext) :
                break

        fileObj.seek(0)

    except Exception, err:
        LOG.error('Exception: %r' % (err))
        LOG.debug(traceback.format_exc())
        fileObj.close()
        return -1

    dataStr=''
    dataStr = "%s" % ("\n").join(['%s' % (str(lines)) for lines in dataList])

    return dataStr


def check_exe(exeName):
    ''' Check that a required executable is in the path...'''    
    try:
        retVal = sh(['which',exeName])
        LOG.debug("{} is in the PATH...".format(exeName))
    except CalledProcessError:
        LOG.error("Required executable {} is not in the path or is not installed, aborting."
                .format(exeName))
        sys.exit(1)


def check_exe2(program):
    ''' Check that a required executable is in the path...'''    
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def retrieve_NCEP_grib_files(Level1D_obj):
    ''' Download the GRIB files which cover the dates of the geolocation files.'''

    ANC_SCRIPTS_PATH = path.join(CSPP_RT_HOME,'scripts','ANC')

    # Check that we have access to the c-shell...
    csh_exe = 'csh'
    #_ = check_exe(csh_exe)
    if check_exe2(csh_exe) is None:
        LOG.error("Required executable '{}' is not in the path or is not installed..."
            .format(csh_exe))
        return -1

    LOG.info('Retrieving and granulating ancillary data for {}...'
            .format(Level1D_obj.input_file))

    # Check that we have access to the GRIB retrieval scripts...
    scriptNames = [
                   'get_anc_iapp_grib1_gdas_gfs.csh'
                  ]
    for scriptName in scriptNames:
        scriptPath = path.join(ANC_SCRIPTS_PATH,scriptName)
        LOG.debug('Checking {}...'.format(scriptPath))
        if not path.exists(scriptPath):
            LOG.error('GRIB ancillary retrieval script {} can not be found, aborting.'
                    .format(scriptPath))
            #sys.exit(1)

    # Get the time stamp for the input file
    dateStamp = Level1D_obj.timeObj_start.strftime("%Y%m%d")

    timeObj = datetime.utcnow()
    now_time_stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    script_args = '{} {}'.format(
            Level1D_obj.timeObj_mid.strftime("%Y%j"),
            Level1D_obj.timeObj_mid.strftime("%H%M")
            )
    LOG.debug('Script args: {}'.format(script_args))
    LOG.debug('JPSS_REMOTE_ANC_DIR: {}'.format(JPSS_REMOTE_ANC_DIR))

    gribFiles = []

    try :
        LOG.info('Retrieving NCEP files for {} ...'
                .format(Level1D_obj.pass_mid_str))
        cmdStr = '{} {}'.format(scriptPath,script_args)
        LOG.debug('\t{}'.format(cmdStr))
        args = shlex.split(cmdStr)

        procRetVal = 0
        procObj = subprocess.Popen(args, \
                env=env(CSPP_EDR_ANC_CACHE_DIR=CSPP_RT_ANC_CACHE_DIR,CSPP_RT_HOME=CSPP_RT_HOME, \
                JPSS_REMOTE_ANC_DIR=JPSS_REMOTE_ANC_DIR), \
                bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode

        procOutput = procObj.stdout.readlines()

        for lines in procOutput:
            LOG.debug(lines)
            if "GDAS/GFS file" in lines :
                lines = string.replace(lines,'GDAS/GFS file: ','')
                lines = string.replace(lines,'\n','')
                gribFiles.append(lines)

        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Retrieval of ancillary files failed for {}.'
                    .format(Level1D_obj.pass_mid_str))
            #sys.exit(procRetVal)

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())

    ## Uniqify the list of GRIB files
    gribFiles = list(set(gribFiles))
    gribFiles.sort()

    for gribFile in gribFiles :
        LOG.info('Retrieved GRIB file: {}'.format(gribFile))

    return gribFiles


def transcode_NCEP_grib_files(grib1_file,work_dir,log_dir):

    IAPP_DECODERS_PATH=path.abspath(path.join(IAPP_HOME,'decoders'))
    LOG.debug('IAPP_DECODERS_PATH : {}'.format(IAPP_DECODERS_PATH))

    IAPP_SCRIPTS_PATH = path.join(CSPP_RT_HOME,'scripts','ANC')
    LOG.debug('IAPP_SCRIPTS_PATH : {}'.format(IAPP_SCRIPTS_PATH))

    IAPP_FILES_PATH=path.abspath(path.join(IAPP_HOME,'decoders','files'))
    LOG.debug('IAPP_FILES_PATH : {}'.format(IAPP_FILES_PATH))
    
    NCGEN_PATH=path.abspath(path.join(CSPP_RT_HOME,'common','ShellB3','bin'))
    LOG.debug('NCGEN_PATH : {}'.format(NCGEN_PATH))
    
    GRIB_FILE_PATH=path.abspath(path.dirname(grib1_file))
    LOG.debug('GRIB_FILE_PATH : {}'.format(GRIB_FILE_PATH))

    # Check that we have access to the k-shell...
    ksh_exe = 'ksh'
    #_ = check_exe(ksh_exe)
    if check_exe2(ksh_exe) is None:
        LOG.error("Required executable '{}' is not in the path or is not installed..."
            .format(ksh_exe))
        return -1

    # Check that we have access to the transcoding script...
    scriptNames = [
                   'iapp_grib1_to_netcdf.ksh'
                  ]
    for scriptName in scriptNames:
        scriptPath = path.join(IAPP_SCRIPTS_PATH,scriptName)
        LOG.debug('Checking {} ...'.format(scriptPath))
        if not path.exists(scriptPath):
            LOG.error('GRIB transcoding script {} can not be found, aborting.'
                    .format(scriptPath))
            return -1

    # Set up the logging
    d = datetime.now()
    timestamp = d.isoformat()
    timestamp = timestamp.replace(":","")
    logname= "iapp_grib2nc."+timestamp+".log"
    logpath= path.join(work_dir, logname )
    logfile_obj = open(logpath,'w')

    current_dir = os.getcwd()

    script_args = '{} {}/iapp_ancillary.cdl'.format(
            grib1_file,
            IAPP_FILES_PATH
            )

    try :
        # Call the transcoding script, writing the logging output to a file
        LOG.info('Transcoding NCEP file {} to NetCDF...'.format(grib1_file))
        cmdStr = '{} {}'.format(scriptPath,script_args)
        LOG.debug('\t{}'.format(cmdStr))
        args = shlex.split(cmdStr)

        os.chdir(work_dir)

        procRetVal = 0
        procObj = subprocess.Popen(args,
                env=env(
                    IAPP_DECODERS_PATH=IAPP_DECODERS_PATH,
                    NCGEN_PATH=NCGEN_PATH
                    ),
                bufsize=0, stdout=logfile_obj, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode

        logfile_obj.close()

        os.chdir(current_dir)

        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Transcoding NCEP file {} to NetCDF failed, aborting...'
                    .format(grib1_file))
            return -1

        # Parse the logfile to determine the new NetCDF filename    
        logfile_obj = open(logpath,'r')
        search_str = "Successfully transcoded to NetCDF file: "
        for lines in logfile_obj:
            if search_str in lines :
                lines = string.replace(lines,search_str,'')
                lines = string.replace(lines,'\n','')
                grib_netcdf_file = lines
                break
        logfile_obj.close()

        os.chdir(current_dir)

        grib_netcdf_local_file = path.join(work_dir,grib_netcdf_file)
        grib_netcdf_remote_file = path.join(GRIB_FILE_PATH,grib_netcdf_file)

        LOG.info('New NetCDF file successfully created: {}'.format(grib_netcdf_local_file))

        # Move the new NetCDF file to the ancillary cache...
        if not path.exists(grib_netcdf_local_file):
            LOG.error('New NetCDF file {} does not exist...'.format(grib_netcdf_local_file))
            LOG.error('New NetCDF file creation failed, aborting...')
            return -1
        else:
            LOG.debug('New local NetCDF file {} exists'.format(grib_netcdf_local_file))

        # Check for remote NetCDF file, and remove if it exists
        if path.exists(grib_netcdf_remote_file):
            LOG.debug('Remote NetCDF file {} exists, removing...'.format(grib_netcdf_remote_file))
            os.unlink(grib_netcdf_remote_file)

        # Move the new NetCDF file to the ancillary cache
        LOG.debug('Moving {} to {}...'.format(
            grib_netcdf_local_file,grib_netcdf_remote_file
            ))
        move(grib_netcdf_local_file,grib_netcdf_remote_file)

        # Remove the temporary NetCDF generation files
        for files in ['ancillary.data','ancillary.info','gribparm.lis']:
            temp_file = path.join(work_dir,files)
            if path.exists(temp_file):
                LOG.debug('Removing temporary NetCDF generation file {}'.format(temp_file))
                os.unlink(temp_file)


    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())

    return grib_netcdf_remote_file


def retrieve_METAR_files(Level1D_obj,GRIB_FILE_PATH):
    ''' Retrieve the METAR Surface Observation ancillary data which 
    cover the dates of the geolocation files.'''

    LOG.info('Retrieving METAR Surface Observation ancillary data for {}...'
            .format(Level1D_obj.input_file))

    # Get the time stamp for the input file
    dateStamp = Level1D_obj.timeObj_start.strftime("%Y%m%d")

    timeObj = datetime.utcnow()
    now_time_stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    LOG.debug('JPSS_REMOTE_ANC_DIR: {}'.format(JPSS_REMOTE_ANC_DIR))

    try :
        LOG.info('Retrieving METAR files for {} ...'
                .format(Level1D_obj.pass_mid_str))
        metarFiles = glob(path.join(GRIB_FILE_PATH,'METAR*'))

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())

    ## Uniqify the list of METAR files
    metarFiles = list(set(metarFiles))
    metarFiles.sort()

    for metarFile in metarFiles :
        LOG.info('Retrieved METAR file: {}'.format(metarFiles))

    if metarFiles == []:
        LOG.error('No METAR surface observation files retrieved for date {}, aborting.'
                .format(Level1D_obj.pass_mid_str))
        sys.exit(1)

    return metarFiles


def transcode_METAR_files(metar_file,work_dir,log_dir):

    IAPP_DECODERS_PATH=path.abspath(path.join(IAPP_HOME,'decoders','bin'))
    LOG.debug('IAPP_DECODERS_PATH : {}'.format(IAPP_DECODERS_PATH))

    IAPP_FILES_PATH=path.abspath(path.join(IAPP_HOME,'decoders','files'))
    LOG.debug('IAPP_FILES_PATH : {}'.format(IAPP_FILES_PATH))
    
    NCGEN_PATH=path.abspath(path.join(CSPP_RT_HOME,'common','ShellB3','bin'))
    LOG.debug('NCGEN_PATH : {}'.format(NCGEN_PATH))
    
    METAR_FILE_PATH=path.abspath(path.dirname(metar_file))
    LOG.debug('METAR_FILE_PATH : {}'.format(METAR_FILE_PATH))

    # Set up the logging
    d = datetime.now()
    timestamp = d.isoformat()
    timestamp = timestamp.replace(":","")
    logname= "iapp_metar_to_nc."+timestamp+".log"
    logpath= path.join(log_dir, logname )
    logfile_obj = open(logpath,'w')

    current_dir = os.getcwd()
    os.chdir(work_dir)

    # Check that we have access to the NetCDF generation exe...
    scriptPath = "{}/ncgen".format(NCGEN_PATH)
    if not path.exists(scriptPath):
        LOG.error('{} can not be found, aborting.'.format(scriptPath))
        sys.exit(1)

    # Construct the command line args to ncgen
    metar_netcdf_file = "{}.nc".format(metar_file)
    script_args = '-b {}/metar_grid.cdl -o {}'.format(
            IAPP_FILES_PATH,
            metar_netcdf_file
            )

    try :
        # Check for existing METAR NetCDF file, and remove if it exists
        if path.exists(metar_netcdf_file):
            LOG.debug(' METAR NetCDF file {} exists, removing...'
                    .format(metar_netcdf_file))
            os.unlink(metar_netcdf_file)

        # Call the NetCDF template generation exe, writing the logging output to a file
        LOG.info('Creating NetCDF template file {} ...'.format(metar_netcdf_file))
        cmdStr = '{} {}'.format(scriptPath,script_args)
        LOG.debug('\t{}'.format(cmdStr))
        args = shlex.split(cmdStr)


        procRetVal = 0
        procObj = subprocess.Popen(args,
                env=env(
                    NCGEN_PATH=NCGEN_PATH
                    ),
                bufsize=0, stdout=logfile_obj, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode


        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Creating NetCDF template file {} failed, aborting...'
                    .format(metar_netcdf_file))
            sys.exit(procRetVal)

        LOG.info('New NetCDF file successfully created: {}'.format(metar_netcdf_file))

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())


    # Get the METAR time information
    metar_year_jday_str = string.split(path.basename(metar_netcdf_file),'.')[1]
    LOG.debug('metar_year_jday_str : {}'.format(metar_year_jday_str))

    metar_UTC_str = string.split(path.basename(metar_netcdf_file),'.')[2]
    LOG.debug('metar_UTC_str : {}'.format(metar_UTC_str))
    
    metar_timeObj = datetime.strptime(
            "{}.{}".format(metar_year_jday_str,metar_UTC_str),
            '%y%j.%H%M')

    metar_time_str = metar_timeObj.strftime("%Y-%m-%d %H:%M:%S.%f")
    LOG.debug("metar_time_str: {}".format(metar_time_str))

    metar_year_str = metar_timeObj.strftime("%y")
    LOG.debug('metar_year_str : {}'.format(metar_year_str))

    metar_month_str = metar_timeObj.strftime("%m")
    LOG.debug('metar_month_str : {}'.format(metar_month_str))

    # Check that we have access to the NetCDF generation exe...
    scriptPath = "{}/drvmetar".format(IAPP_DECODERS_PATH)
    if not path.exists(scriptPath):
        LOG.error('{} can not be found, aborting.'.format(scriptPath))
        sys.exit(1)

    # Construct the command line args to drvmetar
    station_ident_file = path.join(IAPP_FILES_PATH,'sfmetar_sa.tbl')
    script_args = '{} {} {} {}'.format(
            metar_file,
            metar_year_str,
            metar_month_str,
            station_ident_file
            )

    try :
        # Call the METAR to NetCDF transcoding exe, writing the logging output to a file
        LOG.info('Creating METAR NetCDF file {} ...'.format(metar_netcdf_file))
        cmdStr = '{} {}'.format(scriptPath,script_args)
        LOG.debug('\t{}'.format(cmdStr))
        args = shlex.split(cmdStr)

        os.chdir(work_dir)

        procRetVal = 0
        procObj = subprocess.Popen(args,
                env=env(
                    IAPP_DECODERS_PATH=IAPP_DECODERS_PATH,
                    ),
                bufsize=0, stdout=logfile_obj, stderr=subprocess.STDOUT)
        procObj.wait()
        procRetVal = procObj.returncode


        # TODO : On error, jump to a cleanup routine
        if not (procRetVal == 0) :
            LOG.error('Creating NetCDF template file {} failed, aborting...'
                    .format(metar_netcdf_file))
            sys.exit(procRetVal)

        LOG.info('New NetCDF file successfully created: {}'.format(metar_netcdf_file))

    except Exception, err:
        LOG.warn( "{}".format(str(err)))
        LOG.debug(traceback.format_exc())

    logfile_obj.close()

    os.chdir(current_dir)

    return metar_netcdf_file


#!/usr/bin/env python
# encoding: utf-8
"""
$Id: iapp_utils.py 2351 2015-02-11 18:47:51Z geoffc $

Purpose: Common routines for IAPP Level1/2 handling and ancillary data caching.

Created Oct 2011 by R.K.Garcia <rayg@ssec.wisc.edu>
Copyright (c) 2011 University of Wisconsin Regents.
Licensed under GNU GPLv3.
"""

import os
import sys
import logging
import glob
import traceback
import time
import types
import fileinput

from subprocess import Popen, CalledProcessError, call, PIPE
import datetime

import h5py
import __main__
#import npp_orb_num


LOG = logging.getLogger('iapp_utils')

# Table of common ADL SDR log error messages and the associated hint to correcting the problem.
# Algorithm-specific error messages should not go here.
COMMON_LOG_CHECK_TABLE = [
    ("ERROR - CMN GEO set up ephemeris and attitude failure","Check Polar and TLE data"), \
    ("ERROR - CMN GEO satellite position and attitude failure","Problem with S/C Diary"), \
    ("PRO_FAIL Required input not available","Missing or out of date ancillary input"),
    ("PRO_FAIL runAlgorithm()","Algorithm failed"),
    ("Completed unsuccessfully","Algorithm failed"),
    ("The DMS directory is not valid:","Is anc/static data installed?, Is anc/cache data installed? Check DMS path setting in configuration."),
    ("arbitrary time is invalid","Problem with input RDR, check NPP_GRANULE_ID_BASETIME"),
    ("Error retrieving data for USNO-POLARWANDER-UT1","POLAR WANDER file needs update, check NPP_GRANULE_ID_BASETIME"),
    ("Verify that the correct TLE data file has been retrieved", "TLE file needs update, check NPP_GRANULE_ID_BASETIME"),
    ]

PROFILING_ENABLED = os.environ.get('CSPP_PROFILE', None) is not None
STRACE_ENABLED = os.environ.get('CSPP_STRACE', None) is not None




# ref: http://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams
class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevels, reject):
        self.passlevels = set(passlevels)
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno not in self.passlevels)
        else:
            return (record.levelno in self.passlevels)

def _ldd_verify(exe):
    "check that a program is ready to run"
    rc = call(['ldd', exe], stdout=os.tmpfile(), stderr=os.tmpfile())
    return (rc==0)


def split_search_path(s):
    "break a colon-separated list of directories into a list of directories, else empty-list"
    if not s: return []
    
    back_list=[]
    for path in s.split(':' ) :
        back_list.append( os.path.abspath(path) )
  
    return back_list

def _replaceAll(file,searchExp,replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)
    fileinput.close()

#    ("RangeDateTime" DATETIMERANGE EQ "2014-01-13 11:22:39.900000" "2014-01-13 11:22:59.900000")

class AscLineParser(object):

    def time_range(self, ascLine):
        day, time = self.extract_time_range_tokens(ascLine)
        return self.time_from_tokens(day, time)

    def extract_time_range_tokens(self, ascLine):
        return ascLine.split('"')[3:4][0].split(' ')


    def time_from_tokens(self, day, time):
        dt=datetime.datetime.strptime(day + time, '%Y-%m-%d%H:%M:%S.%f')

        return dt

def _testParser():
    dt = AscLineParser().time_range('("RangeDateTime" DATETIMERANGE EQ "2014-01-13 11:22:39.900000" "2014-01-13 11:22:59.900000")')
    print dt


def check_and_convert_path(key,a_path,check_write=False):
    """
    Make sure the path or paths specified exist
    Return the path or list of absolute paths that exist
    """
    abs_locations=[]
    if  ":" in a_path :
        paths=a_path.split(":")
    elif isinstance(a_path, types.StringTypes) == True:
        paths = [a_path] 
    else :
        paths = a_path

    for path in paths:
        if not os.path.exists(path):
            LOG.error("Environment variable %s refers to a path that does not exists.  %s=%s" %(key,key,path))
            LOG.error("Make sure package HOME variable is set and the package home environment script is sourced.")
            sys.exit(2)
        else :
            LOG.debug("Found: %s at %s %s"%(key,path,os.path.abspath(path)))
            abs_locations.append(os.path.abspath(path))
           
        if check_write == True :    
            if not os.access(path, os.W_OK) :
                LOG.error("Path exists but is not writable %s=%s"%(key,path))
                sys.exit(2)
                
    # return a string if only one and an array if more
    if  len(abs_locations) == 1 :
        return abs_locations[0]
    else :
        #return abs_locations
        # return a :-joined string for use in an env variable
        return ':'.join(abs_locations)

 
def check_existing_env_var( varname,default_value=None ):
    """
    Check for vaiable if it exists use vale otherwise use default
    """
    value=None
 
    if varname  in os.environ:
        value=os.environ.get(varname)
    else :
        if default_value != None :
            value=default_value
        else :
            print >>sys.stderr, "ERROR: %s is not set, please update environment and re-try" % varname
            LOG.error("Environment variable missing. %s"%varname)
            sys.exit(9)

    return value


def check_and_convert_env_var(varname,check_write=False,default_value=None):
    value = check_existing_env_var( varname,default_value=default_value )
    path = check_and_convert_path(varname,value,check_write=check_write)
    return path
      

def what_package_am_i():
    file_path= sys.argv[0]
    LOG.debug("Script location is {}".format(file_path))

    cspp_x = file_path.split("/scripts/iapp_level2.py")
    cspp_x_home = cspp_x[0]
    LOG.debug("capp_x_home path is {}".format(cspp_x_home))

    return cspp_x_home
  
#ADL_VARS={}
EXTERNAL_BINARY={}

##named tuple
DDS_PRODUCT_FILE=None
#ADL_HOME=None


IAPP_VARS={}
IAPP_HOME=None

def initialize_IAPP_variables(cspp_xdr_home) :
    global IAPP_HOME
    global DDS_PRODUCT_FILE
    global IAPP_VARS
    
    default=os.path.join(cspp_xdr_home,"common","IAPP_VENDOR")
    IAPP_HOME                = check_and_convert_env_var('IAPP_HOME',check_write=False,default_value=default)
    IAPP_VARS['IAPP_HOME']    = IAPP_HOME

    for key in IAPP_VARS.iterkeys():
        os.environ[key]=IAPP_VARS[key]
        LOG.info("Var "+os.environ[key])
    

CSPP_RT_ANC_CACHE_DIR   = None
CSPP_RT_ANC_PATH        = None
CSPP_RT_ANC_HOME        = None
CSPP_RT_ANC_TILE_PATH   = None
JPSS_REMOTE_ANC_DIR     = None

CSPP_PATHS={}

def check_anc_cache(check_write=True):
    default=os.path.join(CSPP_RT_HOME,"anc/cache")
    CSPP_RT_ANC_CACHE_DIR  = check_and_convert_env_var('CSPP_RT_ANC_CACHE_DIR',check_write=check_write,default_value=default)

   
def initialize_cspp_variables(cspp_home) :
    global CSPP_RT_ANC_TILE_PATH  
    global CSPP_RT_ANC_CACHE_DIR  
    global CSPP_RT_ANC_PATH
    global CSPP_RT_ANC_HOME
    global NAGG                    
    global REPACK
    global JPSS_REMOTE_ANC_DIR
           
    global CSPP_PATHS
    global EXTERNAL_BINARY

    default=os.path.join(cspp_home,"anc/cache")
    CSPP_RT_ANC_CACHE_DIR  = check_and_convert_env_var('CSPP_RT_ANC_CACHE_DIR',check_write=False,default_value=default)
    
    default=os.path.join(cspp_home,"anc/cache/luts")
    CSPP_RT_ANC_PATH       = check_and_convert_env_var('CSPP_RT_ANC_PATH',check_write=False,default_value=default)

    default=os.path.join(cspp_home,"anc/static")
    CSPP_RT_ANC_HOME       = check_and_convert_env_var('CSPP_RT_ANC_HOME',check_write=False,default_value=default)
    default=os.path.join(cspp_home,"anc","static")
    CSPP_RT_ANC_TILE_PATH  = check_and_convert_env_var('CSPP_RT_ANC_TILE_PATH',check_write=False,default_value=default)

    #default="http://jpssdb.ssec.wisc.edu/cspp_v_2_0/ancillary"
    default="ftp://ftp.ssec.wisc.edu/pub/eosdb/ancillary"
    JPSS_REMOTE_ANC_DIR    = check_existing_env_var( "JPSS_REMOTE_ANC_DIR",default_value=default )


def check_env(  work_dir ):
    " Check that needed environment variables are set"
        
    for key in EXTERNAL_BINARY.iterkeys():
        if not _ldd_verify(EXTERNAL_BINARY[key]):
            LOG.warning("%r executable is unlikely to run, is LD_LIBRARY_PATH set?" % EXTERNAL_BINARY[key])

logging_configured=False


def configure_logging(level=logging.WARNING, FILE=None):
    "route logging INFO and DEBUG to stdout instead of stderr, affects entire application"
    global logging_configured

    # create a formatter to be used across everything
    #if level == logging.ERROR : print "logging is ERROR"
    #if level == logging.WARN : print "logging is WARN"
    #if level == logging.INFO : print "logging is INFO"
    #if level == logging.DEBUG : print "logging is DEBUG"

    if level == logging.DEBUG :
        fm = logging.Formatter('%(asctime)s.%(msecs)03d (%(levelname)s) : %(filename)s : %(funcName)s : %(lineno)d:%(message)s',\
                datefmt='%Y-%m-%d %H:%M:%S')
    else:
        fm = logging.Formatter('%(asctime)s.%(msecs)03d (%(levelname)s) : %(message)s',\
                datefmt='%Y-%m-%d %H:%M:%S')

    rootLogger = logging.getLogger()
    
    # set up the default logging
    if logging_configured == False :
        logging_configured=True
        
        # create a handler which routes info and debug to stdout with std formatting
        h1 = logging.StreamHandler(sys.stdout)
        f1 = SingleLevelFilter([logging.INFO, logging.DEBUG], False)
        h1.addFilter(f1)
        h1.setFormatter(fm)

        # create a second stream handler which sends everything else to stderr with std formatting
        h2 = logging.StreamHandler(sys.stderr)
        f2 = SingleLevelFilter([logging.INFO, logging.DEBUG], True)
        h2.addFilter(f2)
        h2.setFormatter(fm)
        rootLogger.addHandler(h1)
        rootLogger.addHandler(h2)
    
    h3= None 
    if FILE != None :
        work_dir=os.path.dirname( FILE )
        check_and_convert_path("WORKDIR",work_dir,check_write=True)
        h3 = logging.FileHandler(filename=FILE)
#        f3 = SingleLevelFilter([logging.INFO, logging.DEBUG], False)
#        h3.addFilter(f3)
        h3.setFormatter(fm)
        rootLogger.addHandler(h3)
        
    rootLogger.setLevel(level)
    

def _test_logging():
    LOG.debug('debug message')
    LOG.info('info message')
    LOG.warning('warning message')
    LOG.error('error message')
    LOG.critical('critical message')


def status_line( status ):
    """
    Make comment standout in log
    """
    LOG.debug("                 ( "+status+" )")


def env(**kv):
    "augment environment with new values"
    zult = dict(os.environ)
    zult.update(kv)

    return zult


def simple_sh(cmd, log_execution=True , *args ,**kwargs):
    "like subprocess.check_call, but returning the pid the process was given"
    if STRACE_ENABLED:
        strace = open('strace.log', 'at')
        print >>strace, "= "*32
        print >>strace, repr(cmd)
        cmd = ['strace'] + list(cmd)
        pop = Popen(cmd, *args, stderr=strace, **kwargs)
    else:
        pop = Popen(cmd, *args, stderr=PIPE, **kwargs)

    pid = pop.pid
    startTime = time.time()
    anc_stderr = pop.communicate()
    rc = pop.returncode

    if rc != 0:
        LOG.error(anc_stderr)

    #rc = pop.wait()
    
    endTime = time.time()
    delta=endTime-startTime
    LOG.debug('statistics for "%s"' % ' '.join(cmd))
    if log_execution == True :
        status_line('Execution Time: %f Sec Cmd "%s"' %(delta, ' '.join(cmd)) )
    
    if rc != 0:       
        exc = CalledProcessError(rc, cmd)
        exc.pid=pid
        raise exc
    
    return pid


def profiled_sh(cmd, log_execution=True, *args, **kwargs):
    """
    like subprocess.check_call, but returning the pid the process was given and 
    logging as INFO the final content of /proc/PID/stat

    """
    pop = Popen(cmd, *args, **kwargs)
    pid = pop.pid
    fn = '/proc/%d/status' % pid
    LOG.debug('retrieving %s statistics to caller dictionary' % fn)
    proc_stats = '-- no /proc/PID/status data --'

    startTime = time.time()
    while True:
        time.sleep(1.0)

        rc = pop.poll()
        if rc is not None:
            break

        try:
            proc = file(fn, 'rt')
            proc_stats = proc.read()
            proc.close()
            del proc
        except IOError as oops:
            LOG.warning('unable to get stats from %s' % fn)

    endTime = time.time()
    delta=endTime-startTime
    LOG.debug('statistics for "%s"' % ' '.join(cmd))
    xml=cmd

    if log_execution == True :
        status_line('Execution Time:  "%f" Sec Cmd "%s"' %(delta, ' '.join(cmd)) )

    LOG.debug(proc_stats)

    if rc != 0:
        exc = CalledProcessError(rc, cmd)
        exc.pid=pid
        raise exc

    return pid


# default sh() is to profile on linux systems
if os.path.exists('/proc') and PROFILING_ENABLED:
    sh = profiled_sh
else:
    sh = simple_sh


def link_ancillary_to_work_dir(work_dir, anc_path_seq):
    """link ancillary files into work directory"""
    for src_path in anc_path_seq:
        _, src_name = os.path.split(src_path)
        tgt_path = os.path.abspath( os.path.join(work_dir, src_name) )

 
        if not os.path.exists(tgt_path):
            LOG.debug('%r -> %r' % (src_name, src_path))
            os.symlink(src_path, tgt_path)
        else:
            LOG.info('%r already exists; continuing' % tgt_path)
        try:
            LOG.debug('testing %r' % tgt_path)
            s = os.stat(tgt_path)
        except OSError as oops:
            LOG.error("link at %r is broken" % tgt_path)
            raise


def get_return_code(num_unpacking_problems, num_xml_files_to_process, 
        num_no_output_runs, noncritical_problem, environment_error):
    """
    based on problems encountered, print final disposition message, return 
    return code to be passed back to caller. Non-zero return code indicates a 
    critical problem was encountered.
    """
    # considered a noncritical problem if there were any runs that crashed, 
    # produced no output, where Geo failed, where ADL logs indicated a problem, 
    # or where output SDRs failed the imaginary quality check

    # critical problems: set non-zero return code and log error messages
    rc = 0
    if num_unpacking_problems > 0:
        rc |= 2
        LOG.error('Failed to unpack input data.')
    if num_xml_files_to_process and (num_xml_files_to_process <= num_no_output_runs): # skipping this check if no XML files to process
        rc |= 1
        LOG.error('Failed to generate any SDR granules.')
    if environment_error:
        rc |= 8
        LOG.error("Environment error.")

    # if critical error was encountered, print failure message and return error code
    if rc != 0:
        LOG.error('Failure. Refer to previous error messages')
        LOG.info('Failure. Refer to previous error messages')        
        return rc

    # otherwise no errors or only non-critical errors: print success message and return 0
    if noncritical_problem:
        LOG.info('Normal Completion. Encountered some problems (refer to previous error messages).')
    else:
        LOG.info('Normal Completion.')
    return rc


# paths for IAPP and ancillary are set to default values based on relative location to this module.

cspp_x_home=what_package_am_i()

# This should be the same as CSPP_IAPP_HOME
CSPP_RT_HOME = check_and_convert_env_var("CSPP_RT_HOME",check_write=False,default_value=cspp_x_home)

initialize_cspp_variables(CSPP_RT_HOME)
initialize_IAPP_variables(CSPP_RT_HOME)


if __name__=='__main__':
    """CSPP_RT_ANC_PATH=/tmp CSPP_RT_ANC_HOME=/tmp CSPP_RT_ANC_CACHE_DIR=/tmp 
       CSPP_RT_ANC_TILE_PATH=/tmp ADL_HOME=/tmp CSPP_RT_HOME=/tmp 
       python adl_common.py >stdout 2>stderr"""
    # logging.basicConfig(level=logging.DEBUG) we don't want basicConfig anymore
    configure_logging(level=logging.DEBUG,FILE="testlog.log")
    _test_logging()
    _test_parser()

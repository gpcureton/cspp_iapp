#!/usr/bin/env python
# encoding: utf-8
"""
iapp_utils.py

Purpose: Common routines for IAPP Level1/2 handling and ancillary data caching.

Copyright (c) 2011 University of Wisconsin Regents.
Licensed under GNU GPLv3.
"""

import os
import sys
import string
import logging
import glob
import traceback
import time
import types
import fileinput

from subprocess import Popen, CalledProcessError, call, PIPE
from datetime import datetime

import h5py
import __main__


LOG = logging.getLogger('iapp_utils')

PROFILING_ENABLED = os.environ.get('CSPP_PROFILE', None) is not None
STRACE_ENABLED = os.environ.get('CSPP_STRACE', None) is not None


class SingleLevelFilter(logging.Filter):
    '''
    ref: http://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams
    '''
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
    return (rc == 0)


def split_search_path(s):
    "break a colon-separated list of directories into a list of directories, else empty-list"
    if not s:
        return []

    back_list = []
    for path in s.split(':'):
        back_list.append(os.path.abspath(path))

    return back_list


def _replaceAll(file, searchExp, replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp, replaceExp)
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
        dt = datetime.strptime(day + time, '%Y-%m-%d%H:%M:%S.%f')

        return dt


def _testParser():
    dt = AscLineParser().time_range(
        '("RangeDateTime" DATETIMERANGE EQ "2014-01-13 11:22:39.900000" "2014-01-13 11:22:59.900000")'
    )
    print dt


class CsppEnvironment(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def check_and_convert_path(key, a_path, check_write=False):
    """
    Make sure the path or paths specified exist
    Return the path or list of absolute paths that exist
    """
    abs_locations = []
    if ":" in a_path:
        paths = a_path.split(":")
    elif isinstance(a_path, types.StringTypes) is True:
        paths = [a_path]
    else:
        paths = a_path

    for path in paths:
        if not os.path.exists(path):
            LOG.error("Environment variable {} refers to a path that does not exists.  {}={}".format(key, key, path))
            LOG.error("Make sure package HOME variable is set and the package home environment script is sourced.")
            sys.exit(2)
        else:
            LOG.debug("Found: {} at {} {}".format(key, path, os.path.abspath(path)))
            abs_locations.append(os.path.abspath(path))

        if check_write is True:
            if not os.access(path, os.W_OK):
                LOG.error("Path exists but is not writable {}={}".format(key, path))
                sys.exit(2)

    # return a string if only one and an array if more
    if len(abs_locations) == 1:
        return abs_locations[0]
    else:
        # return abs_locations
        # return a :-joined string for use in an env variable
        return ':'.join(abs_locations)


def check_existing_env_var(varname, default_value=None):
    """
    Check for vaiable if it exists use vale otherwise use default
    """
    value = None

    if varname in os.environ:
        value = os.environ.get(varname)
    else:
        if default_value is not None:
            value = default_value
        else:
            print >>sys.stderr, "ERROR: %s is not set, please update environment and re-try" % varname
            LOG.error("Environment variable missing. {}".format(varname))
            sys.exit(9)

    return value


def check_and_convert_env_var(varname, check_write=False, default_value=None):
    value = check_existing_env_var(varname, default_value=default_value)
    path = check_and_convert_path(varname, value, check_write=check_write)
    return path


def what_package_am_i():
    file_path = sys.argv[0]
    LOG.debug("Script location is {}".format(file_path))

    cspp_x = file_path.split("/scripts/iapp_level2.py")
    cspp_x_home = cspp_x[0]
    LOG.debug("capp_x_home path is {}".format(cspp_x_home))

    return cspp_x_home


EXTERNAL_BINARY={}

##named tuple
DDS_PRODUCT_FILE=None
#ADL_HOME=None


IAPP_VARS={}
IAPP_HOME=None


def initialize_IAPP_variables(cspp_xdr_home):
    global IAPP_HOME
    global DDS_PRODUCT_FILE
    global IAPP_VARS

    default = os.path.join(cspp_xdr_home, "common", "IAPP_VENDOR")
    IAPP_HOME = check_and_convert_env_var('IAPP_HOME', check_write=False, default_value=default)
    IAPP_VARS['IAPP_HOME'] = IAPP_HOME

    for key in IAPP_VARS.iterkeys():
        os.environ[key] = IAPP_VARS[key]
        LOG.info("Var " + os.environ[key])


CSPP_RT_ANC_CACHE_DIR = None
CSPP_RT_ANC_PATH = None
CSPP_RT_ANC_HOME = None
CSPP_RT_ANC_TILE_PATH = None
JPSS_REMOTE_ANC_DIR = None

CSPP_PATHS = {}


def check_anc_cache(check_write=True):
    default = os.path.join(CSPP_RT_HOME, "anc/cache")
    CSPP_RT_ANC_CACHE_DIR = check_and_convert_env_var('CSPP_RT_ANC_CACHE_DIR', check_write=check_write, default_value=default)


def initialize_cspp_variables(cspp_home):
    global CSPP_RT_ANC_TILE_PATH
    global CSPP_RT_ANC_CACHE_DIR
    global CSPP_RT_ANC_PATH
    global CSPP_RT_ANC_HOME
    global NAGG
    global REPACK
    global JPSS_REMOTE_ANC_DIR

    global CSPP_PATHS
    global EXTERNAL_BINARY

    default = os.path.join(cspp_home, "anc/cache")
    CSPP_RT_ANC_CACHE_DIR = check_and_convert_env_var('CSPP_RT_ANC_CACHE_DIR', check_write=False, default_value=default)

    default = os.path.join(cspp_home, "anc/cache/luts")
    CSPP_RT_ANC_PATH = check_and_convert_env_var('CSPP_RT_ANC_PATH', check_write=False, default_value=default)

    default = os.path.join(cspp_home, "anc/static")
    CSPP_RT_ANC_HOME = check_and_convert_env_var('CSPP_RT_ANC_HOME', check_write=False, default_value=default)
    default = os.path.join(cspp_home, "anc", "static")
    CSPP_RT_ANC_TILE_PATH = check_and_convert_env_var('CSPP_RT_ANC_TILE_PATH', check_write=False, default_value=default)

    # default="http://jpssdb.ssec.wisc.edu/cspp_v_2_0/ancillary"
    default = "ftp://ftp.ssec.wisc.edu/pub/eosdb/ancillary"
    JPSS_REMOTE_ANC_DIR = check_existing_env_var("JPSS_REMOTE_ANC_DIR", default_value=default)


def check_env(work_dir):
    " Check that needed environment variables are set"

    for key in EXTERNAL_BINARY.iterkeys():
        if not _ldd_verify(EXTERNAL_BINARY[key]):
            LOG.warning("%r executable is unlikely to run, is LD_LIBRARY_PATH set?" % EXTERNAL_BINARY[key])


logging_configured = False


def configure_logging(level=logging.WARNING, FILE=None):
    "route logging INFO and DEBUG to stdout instead of stderr, affects entire application"
    global logging_configured

    # create a formatter to be used across everything
    #if level == logging.ERROR : print "logging is ERROR"
    #if level == logging.WARN : print "logging is WARN"
    #if level == logging.INFO : print "logging is INFO"
    #if level == logging.DEBUG : print "logging is DEBUG"

    if level == logging.DEBUG:
        fm = logging.Formatter(
            '%(asctime)s.%(msecs)03d (%(levelname)s) : %(filename)s : %(funcName)s : %(lineno)d:%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        fm = logging.Formatter(
            '%(asctime)s.%(msecs)03d (%(levelname)s) : %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')

    rootLogger = logging.getLogger()

    # set up the default logging
    if logging_configured is False:
        logging_configured = True

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

    h3 = None
    if FILE is not None:
        work_dir = os.path.dirname(FILE)
        check_and_convert_path("WORKDIR", work_dir, check_write=True)
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


def status_line(status):
    """
    Make comment standout in log
    """
    LOG.debug("                 ( " + status + " )")


def env(**kv):
    "augment environment with new values"
    zult = dict(os.environ)
    zult.update(kv)

    return zult


def simple_sh(cmd, log_execution=True, *args, **kwargs):
    "like subprocess.check_call, but returning the pid the process was given"
    if STRACE_ENABLED:
        strace = open('strace.log', 'at')
        print >>strace, "= " * 32
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

    # rc = pop.wait()

    endTime = time.time()
    delta = endTime - startTime
    LOG.debug('statistics for "%s"' % ' '.join(cmd))
    if log_execution is True:
        status_line('Execution Time: %f Sec Cmd "%s"' % (delta, ' '.join(cmd)))

    if rc != 0:
        exc = CalledProcessError(rc, cmd)
        exc.pid = pid
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
    delta = endTime - startTime
    LOG.debug('statistics for "%s"' % ' '.join(cmd))
    xml = cmd

    if log_execution is True:
        status_line('Execution Time:  "%f" Sec Cmd "%s"' % (delta, ' '.join(cmd)))

    LOG.debug(proc_stats)

    if rc != 0:
        exc = CalledProcessError(rc, cmd)
        exc.pid = pid
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
        tgt_path = os.path.abspath(os.path.join(work_dir, src_name))

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
    if num_xml_files_to_process and (num_xml_files_to_process <= num_no_output_runs):  # skipping this check if no XML files to process
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

def make_time_stamp_d(timeObj):
    """
    Returns a timestamp ending in deciseconds
    """
    dateStamp = timeObj.strftime("%Y-%m-%d")
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    deciSeconds = int(round(float(timeObj.microsecond)/100000.))
    deciSeconds = repr(0 if deciSeconds > 9 else deciSeconds)
    timeStamp = "{}.{}".format(timeObj.strftime("%H:%M:%S"),deciSeconds)
    return "{} {}".format(dateStamp,timeStamp)


def make_time_stamp_m(timeObj):
    """
    Returns a timestamp ending in milliseconds
    """
    dateStamp = timeObj.strftime("%Y-%m-%d")
    seconds = repr(int(round(timeObj.second + float(timeObj.microsecond)/1000000.)))
    milliseconds = int(round(float(timeObj.microsecond)/1000.))
    milliseconds = repr(000 if milliseconds > 999 else milliseconds)
    timeStamp = "{}.{}".format(timeObj.strftime("%H:%M:%S"),str(milliseconds).zfill(3))
    return "{} {}".format(dateStamp,timeStamp)

import threading
from threading import Thread, Event
from Queue import Queue, Empty

class NonBlockingStreamReader:
    """
    Implements a reader for a data stream (associated with a subprocess) which
    does not block the process. This is done by writing the stream to a queue
    (decoupling the stream from the reading), and then slurping data off of the
    queue and passing it to wherever it's needed.
    """

    def __init__(self, stream):
        '''
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        '''

        self.stream = stream
        self.queue = Queue()

        def _populateQueue(stream, queue):
            '''
            Collect lines from 'stream' and put them in 'queue'.
            '''

            try:
                while True:
                    line = stream.readline()
                    if line:
                        queue.put(line)
                    else:
                        raise UnexpectedEndOfStream
                        pass
            except UnexpectedEndOfStream:
                LOG.debug("The process output stream has ended.")
            except ValueError:
                LOG.debug("ValueError: The process output stream has ended.")

        self.thread = Thread(target = _populateQueue, args = (self.stream, self.queue))
        self.thread.daemon = True
        self.thread.start() #start collecting lines from the stream

    def readline(self, timeout = None):
        try:
            return self.queue.get(block = timeout is not None,
                    timeout = timeout)
        except Empty:
            #print "Need to close the thread"
            return None

class UnexpectedEndOfStream(Exception):
    pass


def execute_binary_captured_inject_io(work_dir, cmd, err_dict, log_execution=True, log_stdout=True,
        log_stderr=True, **kv):
    """
    Execute an external script, capturing stdout and stderr without blocking the
    called script.
    """

    LOG.debug('executing {} with kv={}'.format(cmd, kv))
    pop = Popen(cmd,
                cwd=work_dir,
                env=env(**kv),
                shell=True,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                close_fds=True)

    # wrap pop.std* streams with NonBlockingStreamReader objects:
    nbsr_stdout = NonBlockingStreamReader(pop.stdout)
    nbsr_stderr = NonBlockingStreamReader(pop.stderr)

    error_keys = err_dict['error_keys']
    del(err_dict['error_keys'])
    #temporal_warning_string = "Temporal_Data"
    #temporal_warning = False
    #hdf_too_big_string = "Cannot create HDF writing for SDS"
    #hdf_too_big_warning = False

    # get the output
    out_str = ""
    while pop.poll()==None and nbsr_stdout.thread.is_alive() and nbsr_stderr.thread.is_alive():

        output_stdout = nbsr_stdout.readline(0.01) # 0.01 secs to let the shell output the result

        if output_stdout is not None:
            time_obj = datetime.utcnow()
            time_stamp = make_time_stamp_m(time_obj)
            out_str += "{} (INFO)  : {}".format(time_stamp,output_stdout)

            # Search stdout for exe error strings and pass them to the logger.
            #LOG.info('error_keys = {}'.format(error_keys))
            for error_key in error_keys:
                error_pattern = err_dict[error_key]['pattern']
                if error_pattern in output_stdout:
                    output_stdout = string.replace(output_stdout,"\n","")
                    err_dict[error_key]['count'] += 1

                    if err_dict[error_key]['count_only']:
                        if err_dict[error_key]['count'] < err_dict[error_key]['max_count']:
                            LOG.warn(string.replace(output_stdout,"\n",""))
                        if err_dict[error_key]['count'] == err_dict[error_key]['max_count']:
                            LOG.warn(string.replace(output_stdout,"\n",""))
                            LOG.warn('Maximum number of "{}" messages reached, further instances will be counted only'
                                    .format(error_key))
                    else:
                        LOG.warn(string.replace(output_stdout,"\n",""))
                    break

        output_stderr = nbsr_stderr.readline() # 0.1 secs to let the shell output the result

        if output_stderr is not None:
            time_obj = datetime.utcnow()
            time_stamp = make_time_stamp_m(time_obj)
            stderr_str = "{}".format(output_stderr)
            LOG.error(string.replace(stderr_str,"\n",""))
            out_str += "{} (ERROR) : {}".format(time_stamp,stderr_str)

        if not nbsr_stdout.thread.is_alive():
            #LOG.debug("stdout thread has ended for segment {} of {}".format(kv['segment'],cmd.split(" ")[-1]))
            LOG.debug("stdout thread has ended for {}".format(cmd.split(" ")[-1]))
        if not nbsr_stderr.thread.is_alive():
            #LOG.debug("stderr thread has ended for segment {} of {}".format(kv['segment'],cmd.split(" ")[-1]))
            LOG.debug("stderr thread has ended for {}".format(cmd.split(" ")[-1]))

    # FIXME: Sometimes the nbsr_stdout and nbsr_stderr threads haven't finished
    #        yet.
    try:
        anc_stdout, anc_stderr = pop.communicate()
    except IOError:
        pass

    # Poll for the return code. A "None" value indicates that the process hasn’t terminated yet.
    # A negative value -N indicates that the child was terminated by signal N
    #rc = pop.returncode
    max_rc_poll_attempts = 10
    rc_poll_attempts = 0
    continue_polling = True
    while continue_polling:
        if rc_poll_attempts == max_rc_poll_attempts:
            LOG.warn(
            'Maximum number of attempts ({}) of obtaining geocat return code for {} reached, setting to zero.'
            .format(rc_poll_attempts,cmd.split(" ")[-1],))
            rc = 0
            break

        rc = pop.returncode
        LOG.debug("{} : pop.returncode = {}".format(cmd.split(" ")[-1],rc))
        if rc != None:
            continue_polling = False

        rc_poll_attempts += 1
        time.sleep(0.5)


    LOG.debug("{}: rc = {}".format(cmd.split(" ")[-1],rc))

    return rc, out_str

# paths for IAPP and ancillary are set to default values based on relative location to this module.

cspp_x_home = what_package_am_i()

# This should be the same as CSPP_IAPP_HOME
CSPP_RT_HOME = check_and_convert_env_var("CSPP_RT_HOME", check_write=False, default_value=cspp_x_home)

initialize_cspp_variables(CSPP_RT_HOME)
initialize_IAPP_variables(CSPP_RT_HOME)


if __name__ == '__main__':
    """CSPP_RT_ANC_PATH=/tmp CSPP_RT_ANC_HOME=/tmp CSPP_RT_ANC_CACHE_DIR=/tmp
       CSPP_RT_ANC_TILE_PATH=/tmp ADL_HOME=/tmp CSPP_RT_HOME=/tmp
       python adl_common.py >stdout 2>stderr"""
    # logging.basicConfig(level=logging.DEBUG) we don't want basicConfig anymore
    configure_logging(level=logging.DEBUG, FILE="testlog.log")
    _test_logging()
    _test_parser()

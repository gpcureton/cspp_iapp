# CSPP-IAPP

This document contains instructions for installation and operation of the Community Satellite
Processing Package (CSPP) software package for transforming direct broadcast HIRS data for NOAA-18, NOAA-19,
Metop-A and Metop-B, on Intel Linux computers. The CSPP-IAPP software package contains
binary executable files and supporting static data files, as well as input and output files for
verification of a correct local installation.

## Introduction

### Overview

This document contains instructions for installation and operation
of the Community Satellite Processing Package (CSPP) release of the
International ATOVS Processing Package (IAPP) software for retrieving
atmospheric temperature and moisture profiles, total ozone and other
parameters in both clear and cloudy atmospheres from direct broadcase
(DB) ATOVS radiance measurements.

The IAPP algorithm, which operates on NOAA-18, NOAA-19, Metop-A and
Metop-B data, retrieves the parameters in 4 steps: 1) cloud detection;
2) bias adjustment; 3) regression retrieval; and 4) nonlinear iterative
physical retrieval. A publication by 

[Li, Wolf, Menzel, Zhang, Huang and Achtor, Journal of Applied Meteorology (August 2000)](http://dx.doi.org/10.1175/1520-0450(2000)039%3C1248:GSOTAF%3E2.0.CO;2)
provides details on the algorithm.

This CSPP release provides IAPP version 4.0 (April 2014), adapted and
tested for operation in a real-time direct broadcast environment.
The software contains binary executable files and supporting static
data files, as well as input and output files for verification of a
successful installation. The CSPP-IAPP software is available from the
CSPP website:

http://cimss.ssec.wisc.edu/cspp

Software, test data, and documentation may be downloaded from this web
site. Please use the ‘Contact Us’ form on the website to submit any
questions or comments about CSPP. Source code for the IAPP package is
included in this release.

### System requirements

System requirements for the CSPP-IAPP v1.0 software are as follows:

* Intel or AMD CPU with 64-bit instruction support,

* 1 GB RAM

* CentOS-6 64-bit Linux (or other compatible 64-bit Linux distribution),

* 3 GB of disk space (plus space for your own DB data and CSPP-IAPP products).

* Internet connection (for downloading dynamic ancillary data).

Linux terminal commands included in these instructions are for the bash shell.

### Disclaimer

Original scripts and automation included as part of this package are
distributed under the GNU GENERAL PUBLIC LICENSE agreement version
3\. Binary executable files included as part of this software package
are copyrighted and licensed by their respective organizations, and
distributed consistent with their licensing terms.

The University of Wisconsin-Madison Space Science and Engineering Center
(SSEC) makes no warranty of any kind with regard to the CSPP software or
any accompanying documentation, including but not limited to the implied
warranties of merchantability and fitness for a particular purpose. SSEC
does not indemnify any infringement of copyright, patent, or trademark
through the use or modification of this software.

There is no expressed or implied warranty made to anyone as to the
suitability of this software for any purpose. All risk of use is
assumed by the user. Users agree not to hold SSEC, the University of
Wisconsin-Madison, or any of its employees or assigns liable for any
consequences resulting from the use of the CSPP software.

## Installation and Configuration

### Overview

This software package contains the CSPP-IAPP retrieval system based on
the IAPP version 4.0 software and bundled as a stand-alone processing
package for direct broadcast users.

### Installation of CSPP-IAPP Software

Create the working and tarball directories, and change into the tarball directory...

```[bash]
mkdir tarballs
cd tarballs
```

Download the CSPP-IAPP software and test data tarballs (and associated sha1 checksum files)
from http://cimss.ssec.wisc.edu/cspp/...

```[bash]
wget -c http://www.ssec.wisc.edu/~geoffc/CSPP_IAPP/downloads/CSPP_IAPP_v1.0.tar.gz
wget -c http://www.ssec.wisc.edu/~geoffc/CSPP_IAPP/downloads/CSPP_IAPP_v1.0.tar.gz.sha1
wget -c http://www.ssec.wisc.edu/~geoffc/CSPP_IAPP/downloads/CSPP_IAPP_v1.0_TEST_DATA.tar.gz
wget -c http://www.ssec.wisc.edu/~geoffc/CSPP_IAPP/downloads/CSPP_IAPP_v1.0_TEST_DATA.tar.gz.sha1
```

Using the sha1 files, confirm the integrity of the downloaded tarballs, and change back to the top-level directory...

```[bash]
sha1sum -c CSPP_IAPP_v1.0.tar.gz.sha1
sha1sum -c CSPP_IAPP_v1.0_TEST_DATA.tar.gz.sha1
cd ..
```

Install the package tarball

```[bash]
tar xzvf tarballs/CSPP_IAPP_v1.0.tar.gz
```

Set up the run environment...

```[bash]
export CSPP_IAPP_HOME=CSPP_IAPP_1_0
. $CSPP_IAPP_HOME/cspp_iapp_env.sh
```

CSPP-IAPP is now ready to use, and test data files are included in the
`Work/sample_data` directory.

In order to test the installation, execute the main driver script now with no arguments

```[bash]
bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh
```

If the installation has been successful to this point, you will be presented with CSPP-IAPP
command line switches and options. This does not mean that your installation is processing
data correctly (see Section 3.2), but it does mean that the environment has been successfully
set to start using CSPP-IAPP.


### Implementation Notes:

When installed as shown in section 2.2, the directory/file structure of CSPP-IAPP (pruned for
the purposes of this document) is

```
CSPP_IAPP_1_0
        ├── anc
        │   ├── cache
        │   │   └── luts
        │   └── static
        │
        ├── common
        │   ├── cspp_cfg
        │   ├── IAPP_VENDOR
        │   └── ShellB3
        │
        ├── scripts
        │   ├── ANC
        |   |   ├── get_anc_iapp_gdas_gfs.csh
        |   |   ├── get_anc_iapp_grib1_gdas_gfs.csh
        |   |   ├── iapp_before_and_after_time.csh
        |   |   ├── iapp_grib1_to_netcdf.ksh
        |   |   ├── iapp_grib2_to_netcdf.ksh
        |   |   ├── iapp_retrieve_gdas_gfs.csh
        |   |   ├── __init__.py
        |   |   ├── jpss_before_and_after_time.csh
        |   |   └── Utils.py
        |   |
        │   ├── iapp_compare_netcdf.sh
        │   ├── iapp_level2.py
        │   ├── iapp_level2.sh
        │   └── iapp_utils.py
        │
        ├── cspp_iapp_env.sh
        ├── cspp_iapp_runtime.sh
        └── cspp_iapp_unset.sh
```


Everything beneath `IAPP_VENDOR/` comprises the package IAPP v4.0. Documentation files
from IAPP are provided in directory/files

```
IAPP_VENDOR/iapp/docs
IAPP_VENDOR/iapp/release_note_IAPPv4.0
```

In `IAPP_VENDOR/iapp/docs`, specifically the files are: `IAPP_design.ps`, `iapp_retrievals.ps`,
`iapp_structure.txt` and `subs_description.txt`.

The remainder is the scripting and organization applied by CSPP team to implement IAPP in the
direct broadcast environment. Of interest is the anc/cache directory, in which the downloaded
ancillary NCEP GDAS/GFS files are stored and transcoded.. Over time, the ancillary cache may
use significant disk space: if necessary, this directory can be replaced with a link to another disk
location with greater storage capacity.


### Input Data Requirements

CSPP-IAPP produces single Field-of-Regard (FOR) retrievals from input level 1d
calibrated/geolocated data. The level 1d files must contain radiances/brightness temperatures
from the High Resolution Infrared Radiation Sounder (HIRS), the Advanced Microwave
Sounding Unit-A (AMSU-A), and the Microwave Humidity Sounder (MHS). All three
instruments must be included as part of the level-1d file in order for CSPP-IAPP to
execute correctly.

Supported satellites are:

* NOAA-18,
* NOAA-19,
* Metop-A, and
* Metop-B.

Level 1d files can be generated using the ATOVS and AVHRR Pre-processing Package
(AAPP), available from

http://nwpsaf.eu/deliverables/aapp/



#### Generation of level-1d files using AAPP

The following run commands were used with AAPP v7.8 to create Level 1D files compatible with
this release of IAPP:

* To create HIRS/AMSU/MHS Level 1D files for NOAA-18/19:
```
AAPP_RUN_NOAA -i "HIRS AMSU-A AMSU-B" -g "HIRS" -o $output_dir $hrpt_file
```

* To create HIRS/AMSU/MHS Level 1D files for Metop-A/B:
```
AAPP_RUN_METOP -i "HIRS AMSU-A MHS" -g "HIRS" -d $input_dir -o $output_dir
```

### Dynamic ancillary data for CSPP-IAPP

While the use of dynamic ancillary data is not mandatory for execution of the CSPP-IAPP
software, it is strongly recommended that National Center for Environmental Prediction (NCEP)
Numerical Weather Prediction Global Data Assimilation (GDAS) and/or Global Forecast System
(GFS) grib1 files be used. These 1 degree GRIB1 NWP files are automatically identified and
fetched from the CSPP ancillary data server as part of the data processing based upon the date
and time of the input satellite data. This is the software default behavior. The software requires
one GDAS analysis file or GFS forecast file that most closely matches the date/time of the data
set. A GDAS analysis file will be used if processing archived data. Real-time processing will
use GFS forecast model files, since the GDAS files are not available until 6-9 hours after model
run time.

Example 6 Hour GFS Model Forecast File Name: gfs.tYY.051201.pgrbfXX
    where XX is the forecast time step for the YY hour analysis (run) time.

Example 6 Hour GDAS Model Analysis File Name: gdas1.PGrbF00.020430.YYz
    where YY is the analysis (run) time.

As part of the ancillary data pre-processing the selected GDAS/GFS files are converted to
NetCDF.


## Using CSPP-IAPP

### CSPP-IAPP Driver Script

Bash script `$CSPP_IAPP_HOME/scripts/iapp_level2.sh` checks for environment variable
CSPP_IAPP_HOME and then invokes the Python script `$CSPP_IAPP_HOME/scripts/iapp_level2.py`,
which contains all the remaining logic to organize IAPP processing (i.e.: fetch dynamic ancillary
data, transcode GRIB files to NetCDF, generate NetCDF output templates, linking of the various
input files and LUTs into the working directory, and post execution cleanup). Script
`iapp_level2.sh` requires, at a minimum, the name of the input level-1d file, and the name of the
satellite, in that order...

```[bash]
bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh hirsl1d_M01_20150126_0204_12223.l1d 'metopb'
```

Various command line options are available for `iapp_level2.sh` as shown below:

```
bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh

usage: iapp_level2.py [-h] [-w WORK_DIR] [-t TOPOGRAPHY_FILE]
                      [-f FORECAST_MODEL_FILE] [-r RADIOSONDE_DATA_FILE]
                      [-s SURFACE_OBSV_FILE] [--instrument_combo {1,2,3,4}]
                      [--retrieval_method {0,1}] [--lower_lat LOWER_LATITUDE]
                      [--upper_lat UPPER_LATITUDE] [--left_lon LEFT_LONGITUDE]
                      [--right_lon RIGHT_LONGITUDE] [--print_retrieval]
                      [--print_l1d_header] [--debug] [-v] [-q]
                      input_file {noaa15,noaa16,noaa18,noaa19,metopa,metopb}

Run the IAPP package on level-1d files to generate level-2 files.

positional arguments:
  input_file            The fully qualified path to a single level-1d input
                        file.
  {noaa15,noaa16,noaa18,noaa19,metopa,metopb}
                        Satellite name. Possible values are... 'noaa15',
                        'noaa16', 'noaa18', 'noaa19', 'metopa', 'metopb'.

optional arguments:
  -h, --help            show this help message and exit
  -w WORK_DIR, --work_directory WORK_DIR
                        The directory which all activity will occur in,
                        defaults to the current directory. [default: .]
  -t TOPOGRAPHY_FILE, --topography_file TOPOGRAPHY_FILE
                        The topography file. [default: topography.nc]
  -f FORECAST_MODEL_FILE, --forecast_file FORECAST_MODEL_FILE
                        The GDAS/GFS forecast/analysis file (NetCDF format).
                        [default: None]
  -r RADIOSONDE_DATA_FILE, --radiosonde_file RADIOSONDE_DATA_FILE
                        The radiosonde file. [default: None]
  -s SURFACE_OBSV_FILE, --surface_obs_file SURFACE_OBSV_FILE
                        The METAR surface observation file (NetCDF format).
                        [default: None]
  --instrument_combo {1,2,3,4}
                        Instrument combination. Possible values are... 1:
                        '(HIRS + AMSU-A)', 2: '(AMSU-A only)', 3: '(AMSU-A &
                        MHS only)', 4: '(HIRS, AMSU-A & MHS)'. [default: 4]
  --retrieval_method {0,1}
                        Retrieval method. Possible values are... 0: 'fixed',
                        1: 'dynamic'. [default: 1]
  --lower_lat LOWER_LATITUDE
                        Lower latitude for retrieval. [default: 0.0]
  --upper_lat UPPER_LATITUDE
                        Upper latitude for retrieval. [default: 0.0]
  --left_lon LEFT_LONGITUDE
                        Left longitude for retrieval. [default: 0.0]
  --right_lon RIGHT_LONGITUDE
                        Right longitude for retrieval. [default: 0.0]
  --print_retrieval     Print the running output of the IAPP retrieval.
                        [default: False]
  --print_l1d_header    Print the level 1D header, and exit. [default: False]
  --debug               Enable debug mode and avoid cleaning workspace.
                        [default: False]
  -v, --verbose         each occurrence increases verbosity 1 level from INFO.
                        -v=DEBUG
  -q, --quiet           Silence all output
```

### Running the CSPP-IAPP Test Case

To validate your installation, you can run the CSPP-IAPP test case. First unpack the test data
and create work directories for each satellite…

```[bash]
for dirs in metopa  metopb  noaa15  noaa16  noaa18  noaa19; do mkdir -p Work/$dirs ; done
tar xzvf tarballs/CSPP_IAPP_v1.0_TEST_DATA.tar.gz -C Work
```

and then execute the software

```[bash]
for files in $(ls Work/sample_data/input/noaa15/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'noaa15' -w Work/noaa15 ; \
done
```

```[bash]
for files in $(ls Work/sample_data/input/noaa16/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'noaa16' -w Work/noaa16 ; \
done
```

```[bash]
for files in $(ls Work/sample_data/input/noaa18/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'noaa18' -w Work/noaa18 ; \
done
```

```[bash]
for files in $(ls Work/sample_data/input/noaa19/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'noaa19' -w Work/noaa19 ; \
done
```

```[bash]
for files in $(ls Work/sample_data/input/metopa/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'metopa' -w Work/metopa ; \
done
```

```[bash]
for files in $(ls Work/sample_data/input/metopb/*.l1d); \
do \
    bash $CSPP_IAPP_HOME/scripts/iapp_level2.sh $files 'metopb' -w Work/metopb ; \
done
```

Executing these commands will test the retrieval software on all 4 supported satellite/instrument
groups. There are multiple input test files. The processing for data segment should take just a
few seconds. For each input l1d data segment, one output CSPP-IAPP NetCDF3 file is created.
If the CSPP-IAPP processing script runs normally, it will return a status code equal to zero. If the
CSPP-IAPP processing script encounters a fatal error, it will return a non-zero status code.
To verify your output files against the output files created at UW/SSEC, execute the following
commands (make sure you are in the sample_data directory):

```[bash]
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/metopa Work/metopa
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/metopb Work/metopb
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/noaa15 Work/noaa15
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/noaa16 Work/noaa16
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/noaa18 Work/noaa18
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/noaa19 Work/noaa19
```

This script compares the contents of the `Temperature_Retrieval` array of all of the NetCDF3
work files with the verification files that are included with the package. The number of
differences found for each array will be printed. There should be few, if any differences.

For Metop-A, for example

```[bash]
$CSPP_IAPP_HOME/scripts/iapp_compare_netcdf.sh Work/sample_data/output/metopa Work/metopa
```

you should see...

```
Comparing Temperature_Retrieval array in Work/metopa/metopa_L2_d20150304_t0326149_e0328485_c20150402204101032104_iapp.nc to validation file
SUCCESS: 0 pixels out of 4536 pixels are different
Comparing Temperature_Retrieval array in Work/metopa/metopa_L2_d20150304_t1404324_e1410244_c20150402204111185493_iapp.nc to validation file
SUCCESS: 0 pixels out of 12852 pixels are different
Comparing Temperature_Retrieval array in Work/metopa/metopa_L2_d20150304_t1549108_e1554436_c20150402204120021899_iapp.nc to validation file
SUCCESS: 0 pixels out of 11340 pixels are different
All files passed
SUCCESS
```

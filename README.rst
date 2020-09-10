========================
CSV2B1DDI migration tool
========================

Version: 0.6
Author: John Neerdael
Email: jneerdael@infoblox.com

Description
-----------

This script can be used to import data from NIOS CSV files in to BloxOne DDI.
We expect CSV files per object type (example: networks.csv containing a 
header-network line and the objects which start with network).

Host objects are currently not supported in this script.

Prerequisites
-------------

Python 3.6 or above

Non-standard modules:

    - bloxone 0.5.6+

The latest version of the bloxone module is available on PyPI and can simply be
installed using::

    pip3 install bloxone --user

To upgrade to the latest version::

    pip3 install bloxone --user --upgrade

Complete list of modules::

    import bloxone
    import csv
    import json
    import argparse
    import re
	import ipaddress


Basic Configuration
-------------------

The bloxone module use an ini file for configuration. 

A sample is provided called demo.ini. Unless an alternative is specified on the
command line, the script will automatically use the demo.ini from the current 
working directory if available. 

The format of the ini file is::

    [BloxOne]
    url = 'https://csp.infoblox.com'
    api_version = 'v1'
    api_key = '<Your Region API Key Here>'

    
Once your API key is configured, your username and customer name are set
you are ready to run the script with the required parameters.

Usage
-----

csv2b1ddi.py supports -h or --help on the command line to access the options available::

    $ ./csv2b1ddi.py --help
	usage: csv2b1ddi [-h] [-b NETWORKCONTAINERS] [-n NETWORKS] [-r RANGES] [-f FIXED] [-z AUTHZONES] [-a ARECORD] [-t TXTRECORD] [-m MXRECORD] [-p PTRRECORD] [-s SRVRECORD] [--aaaa AAAARECORD] [--cname CNAMERECORD] [--tags TAGS] -i IPSPACE -c CONFIG [-v]

	This is a simple NIOS to B1DDI migration tool

	optional arguments:
	  -h, --help            show this help message and exit
	  -b NETWORKCONTAINERS, --networkblock NETWORKCONTAINERS
							CSV file with Networks data
	  -n NETWORKS, --networks NETWORKS
							CSV file with Networks data
	  -r RANGES, --ranges RANGES
							CSV file with DHCP ranges data
	  -f FIXED, --fixed FIXED
							CSV file with Fixed Address data
	  -z AUTHZONES, --authzone AUTHZONES
							CSV file with Authoritative Zones data
	  -a ARECORD, --arecord ARECORD
							CSV file with A record data
	  -t TXTRECORD, --txtrecord TXTRECORD
							CSV file with TXT record data
	  -m MXRECORD, --mxrecord MXRECORD
							CSV file with MX record data
	  -p PTRRECORD, --ptrrecord PTRRECORD
							CSV file with PTR record data
	  -s SRVRECORD, --srvrecord SRVRECORD
							CSV file with SRV record data
	  --aaaa AAAARECORD     CSV file with AAAA record data
	  --cname CNAMERECORD   CSV file with AAAA record data
	  --tags TAGS           Tags to apply to imported objects
	  -i IPSPACE, --ipspace IPSPACE
							Name of IP space to import data in
	  -c CONFIG, --config CONFIG
							Path to ini file with API key
	  -v, --version         show program's version number and exit
    
Tags are added in a specific format (note that currently the double quotes need to be escaped):
	$ ./csv2b1ddi-0.5.py --tags '{\"OWNER\":\"jneerdael\",\"LOCATION\":\"Amsterdam\"}'

There is currently no or very little error handling. Please thread with caution, EA's are not imported and tags are currently only supported as shown above.
We except a correct and existing BloxOne DNS view to be present in the CSV files, the ipspace provided through the CLI also needs to be present.
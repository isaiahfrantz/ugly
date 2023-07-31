#!/usr/bin/env python
'''
Ugly monitoring app
    Parameters:
        input_type (string):
        scan_type (string):
        max_agent_pu

'''


# stdlib imports
import getopt
import sys
import re

# ugly module
from ugly_lib import Ugly

# remove first arg/program name
argslist = sys.argv[1:]

# Options
OPTIONS = "hdi:g:s:m:n:t:r:p:o:"
# Long options
long_options = ["help",
                "debug",
                "input_type=",
                "input_target=",
                "scan_type=",
                "max_agent_pull_retries=",
                "nfs_read_dir",
                "storage_type="
                "s3_region=",
                "s3_bucket_prefix=",
                "nfs_write_dir=",
                ]

try:
    # Parse args
    args, values = getopt.getopt(argslist, OPTIONS, long_options)
except getopt.error as err:
        # we hit an error, print details
        pm(f"ERROR: arg parsing error=>{str(err)}<")

# globals and default values
# ARCH = 'ARCH_NOT_SET'
# NUM  = 10

def main(args) -> int:
    # default values:
    input_type = 'nfs'
    input_target = 'path-to-ip-lists.txt'
    scan_type = 'agent-pull'
    max_agent_pull_retries = 10
    nfs_read_dir = '/nfs/agent-output'
    storage_type = 's3'
    s3_region = 'eu-west-1'
    s3_bucket_prefix = 'ip-scanner-results'
    nfs_write_dir = '/nfs/ip-scanner-results'

    # check args
    for arg, val in args:
        if arg in ("-h", "--help"):
            pm("Display help")
            show_help()

        elif arg in ("-d", "--debug"):
            pm("Enable debug output")
            u.DEBUG = True

        elif arg in ("-i", "--input_type"):
            input_type = val
            # TODO add validation code:
            # can be 'nfs' or 'api'

        elif arg in ("-g", "--input_target"):
            input_target = val
            # TODO add validation code:
            # if input_type == nfs, should be a file that exists
            # if input_type == api, should be valid uri (test existence later in )

        elif arg in ("-s", "--scan_type"):
            scan_type = val
            # TODO add validation code
            # can be 'agent-pull' or 'nfs-read'

        elif arg in ("-m", "--max_agent_pull_retries"):
            max_agent_pull_retries = val
            # TODO add validation code

        elif arg in ("-n", "--nfs_read_dir"):
            nfs_read_dir = val
            # TODO add validation code

        elif arg in ("-t", "--storage_type"):
            storage_type = val
            # TODO add validation code
            # can be 's3' or 'nfs-write'

        elif arg in ("-r", "--s3_region"):
            s3_region = val
            # TODO add validation code

        elif arg in ("-p", "--s3_bucket_prefix"):
            s3_bucket_prefix = val
            # TODO add validation code

        elif arg in ("-o", "--nfs_write_dir"):
            nfs_write_dir = val
            # TODO add validation code

        # populate ip_list array
        ip_list = None
        if input_type == 'nfs':
            ip_list = u.open_target_file(input_target)
        elif input_type == 'api':
            ip_list = u.open_api(input_target)
        if ip_list is None:
            raise Exception(f"unrecognized input_type {input_type}")

        results = dict()
        if scan_type == 'agent-pull':
            results = u.agent_pull(ip_list, max_agent_pull_retries)
        elif scan_type == 'nfs-read':
            results = u.nfs_read(ip_list, nfs_read_dir)
        else:
            raise Exception(f"unrecognized scan_type {scan_type}")

        if storage_type == 's3':
            u.storeResultsInS3(results, s3_region, s3_bucket_prefix)
        elif storage_type == 'nfs-write':
            u.nfs_write(results, nfs_write_dir)
        else:
            raise Exception(f"unrecognized storage_type {storage_type}")


        return 0

def show_help(exit_code=0):
    '''
    Display help and exit
        Parameters:
            exit_code (int): default is zero, if set will exit with provided exit_code
        Returns:
            None
    '''
    print ("""Args:
    -h,--help                       display this help
    -d,--debug                      print debug output
    -i,--input_type                 where input data is coming from
    -g,--input_target               filename or api uri to get input
    -s,--scan_type                  type of scan
    -m,--max_agent_pull_retries     max retries
    -n,--nfs_read_dir               nfs target dir
    -t,--storage_type               type of storage to write output
    -r,--s3_region                  s3 output region
    -p,--s3_bucket_prefix           s3 output prefix
    -o,--nfs_write_dir              nfs output dir""")
    sys.exit(exit_code)

def pm(message):
    '''
    Handles printing messages
        Parameters:
            message (string):
                If it contains the string DEBUG, print it to stderr only if the global DEBUG is True
                If it doesn't contain DEBUG, print message to stdout as it is
        Returns:
            None
    '''
    if re.search(r"DEBUG",message):
        if DEBUG:
            print(message, file=sys.stderr)
    else:
        print(message)


# start main script
if __name__ == '__main__':
    raise SystemExit(main(args))


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
import os
import re

# ugly client classes
from ugly_lib import *

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

def show_help(exit_code=0):
    '''
    Display help and exit
        Parameters:
            exit_code (int): default is zero, if set will exit with provided exit_code
        Returns:
            None
    '''
    print ("""show_help()
    Args:
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

try:
    # Parse args
    args, values = getopt.getopt(argslist, OPTIONS, long_options)
except getopt.error as err:
        # we hit an error, print details
        pm(f"ERROR: arg parsing error=>{str(err)}<")

# globals and default values
DEBUG = False

def main(args) -> int:
    # get values from env or use defaults before checking for optional cli options
    input_type = os.environ('INPUT_TYPE') if os.environ('INPUT_TYPE') else 'nfs'
    input_target = os.environ('INPUT_TARGET') if os.environ('INPUT_TARGET') else 'path-to-ip-lists.txt'
    # scan_type = 'agent-pull'
    max_agent_pull_retries = os.environ('MAX_AGENT_PULL_RETRIES') if os.environ('MAX_AGENT_PULL_RETRIES') else 10
    nfs_read_dir = os.environ('NFS_READ_DIR') if os.environ('NFS_READ_DIR') else '/nfs/agent-output'
    # storage_type = 's3'
    s3_region = os.environ('S3_REGION') if os.environ('S3_REGION') else 'eu-west-1'
    s3_bucket_prefix = os.environ('S3_BUCKET_PREFIX') if os.environ('S3_BUCKET_PREFIX') else 'ip-scanner-results'
    nfs_write_dir = os.environ('NFS_WRITE_DIR') if os.environ('NFS_WRITE_DIR') else '/nfs/ip-scanner-results'
    debug = os.environ('DEBUG') if os.environ('DEBUG') else False

    # check args
    for arg, val in args:
        if arg in ("-h", "--help"):
            pm("Display help")
            show_help()

        elif arg in ("-d", "--debug"):
            pm("Enable debug output")
            DEBUG = True

        elif arg in ("-i", "--input_type"):
            input_type = val
            # TODO add validation code:
            # can be 'nfs' or 'api'

        elif arg in ("-g", "--input_target"):
            input_target = val
            # TODO add validation code:
            # if input_type == nfs, should be a file that exists
            # if input_type == api, should be valid uri (test existence later in )

        # elif arg in ("-s", "--scan_type"):
        #     scan_type = val
        #     # TODO add validation code
        #     # can be 'agent-pull' or 'nfs-read'

        elif arg in ("-m", "--max_agent_pull_retries"):
            max_agent_pull_retries = val
            # TODO add validation code

        elif arg in ("-n", "--nfs_read_dir"):
            nfs_read_dir = val
            # TODO add validation code

        # elif arg in ("-t", "--storage_type"):
        #     storage_type = val
        #     # TODO add validation code
        #     # can be 's3' or 'nfs-write'

        elif arg in ("-r", "--s3_region"):
            s3_region = val
            # TODO add validation code

        elif arg in ("-p", "--s3_bucket_prefix"):
            s3_bucket_prefix = val
            # TODO add validation code

        elif arg in ("-o", "--nfs_write_dir"):
            nfs_write_dir = val
            # TODO add validation code

        # required arg groups
        required_args = {'input_type', 'input_target'}
        required_arg_by_type = {
                'nfs': {'nfs_read_dir', 'nfs_write_dir'},
                'api': {'max_agent_pull_retries', 's3_region', 's3_bucket_prefix'}
            }

        # Check required input_type args have been defined
        if input_type not in required_arg_by_type.keys():
            raise getopt.GetoptError(f'input_type must be one of=>{Ugly.GetInputTypes}<, got=>{input_type}<')
        for v in required_args + required_arg_by_type[input_type]:
            if v not in locals():
                raise getopt.GetoptError(f'Required arg for input_type=>{input_type}< missing=>{v}<')

        # Warn if args have been defined for the wrong input type
        not_required_args = set(required_arg_by_type.keys()) - set(input_type)
        for k,vars in required_arg_by_type:
            if k == input_type: continue
            for v in vars:
                if v in locals():
                    raise Warning(f'Found arg=>{v}< that is required for input_type=>{k}< but unused for selected input_type=>{input_type}<')

        # create a storage type specific client
        if input_type == 'nfs':
            client = Nfs_client(input_target, nfs_read_dir, nfs_write_dir, DEBUG)
        elif input_type == 'api':
            client = S3_client(input_target, max_agent_pull_retries, s3_region, s3_bucket_prefix, debug)
        else:
            raise Exception(f"unrecognized input_type {input_type}")

        # process the data and write to output storage
        client.process()

        # if we made it this far without an exception, exit 0
        return 0

# start main script
if __name__ == '__main__':
    raise SystemExit(main(args))


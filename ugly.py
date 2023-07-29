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

# ugly module
import ugly_lib as u

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
        u.pm(f"ERROR: arg parsing error=>{str(err)}<")

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
            u.pm("Display help")
            u.show_help()

        elif arg in ("-d", "--debug"):
            u.pm("Enable debug output")
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

# start main script
if __name__ == '__main__':
    raise SystemExit(main(args))


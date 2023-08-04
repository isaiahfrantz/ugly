# ugly
monitoring app

# Usage
The project is comprise of two parts:
 - A wrapper script to handle/parse/validate the cli args
 - A module that contains the classes for reading, processing, and writing validated lists of Ip's to/from NFS or S3 storage

## Options
- -h/--help                       displays help and exits
- -d/--debug                      outputs additional debug info (mostly used during dev time)
- -i,--input_type                 where input data is coming from
- -g,--input_target               filename or api uri to get input
- -s,--scan_type                  type of scan
- -m,--max_agent_pull_retries     max retries
- -n,--nfs_read_dir               nfs target dir
- -t,--storage_type               type of storage to write output
- -r,--s3_region                  s3 output region
- -p,--s3_bucket_prefix           s3 output prefix
- -o,--nfs_write_dir              nfs output dir


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

ip_list = None
if input_type == 'nfs':
    with open('path-to-ip-lists.txt') as fd:
        path_to_ip_lists = fd.read()
    ip_list = []
    for dir_name, subdir_list, file_list in os.walk(path_to_ip_lists):
        for file in file_list:
            with open(file) as fd:
                data = json.load(fd)
            ip_list.extend(data['iplist'])
            for ip in ip_list:
                validateIP(ip)
elif input_type == 'api':
    response = requests.get('https://api/iplist')
    if response.status_code != 200:
        raise Exception('non-200 status code: %d' % response.status_code)
    data = json.loads(response.text)
    ip_list = data['iplist']
    page_counter = 0
    while data['more'] is True:
        page_counter += 1
        response = requests.get('https://api/iplist?page=%d' % page_counter)
        if response.status_code != 200:
            raise Exception('non-200 status code: %d' % response.status_code)
        data = json.loads(response.text)
        ip_list.extend(data['iplist'])
    for ip in ip_list:
        validateIP(ip)
if ip_list is None:
    raise Exception('unrecognized input_type "%s"' % input_type)

results = None
if scan_type == 'agent-pull':
    results = dict()
    for ip in ip_list:
        response = requests.get('https://%s/portdiscovery' % ip)
        if response.status_code != 200:
            raise Exception('non-200 status code: %d' % response.status_code)
        data = json.loads(response.text)
        agent_url = '%s/api/2.0/status' % data['agenturl']
        response = requests.get(agent_url)
        retries = 0
        while response.status_code == 503:
            if retries > max_agent_pull_retries:
                raise Exception('max retries exceeded for ip %s' % ip)
            retries += 1
            time_to_wait = float(response.headers['retry-after'])
            time.sleep(time_to_wait)
            response = requests.get(agent_url)
        if response.status_code != 200:
            raise Exception('non-200 status code: %d' % response.status_code)
        results[ip] = data['status']
elif scan_type == 'nfs-read':
    results = dict()
    for ip in ip_list:
        agent_nfs_path = '%s/%s' % (nfs_read_dir, ip)
        for dir_name, subdir_list, file_list in os.walk(agent_nfs_path):
            for file in file_list:
                with open(file) as fd:
                    data = json.load(fd)
                if 'schema' not in data or float(data['schema']) < 2.0:
                    result = data
                else:
                    result = data['status']
                results[ip] = result
else:
    raise Exception('unrecognized scan_type %s' % scan_type)

def storeResultsInS3(results, region):
    client, bucketname = getorcreatebucketandclient(region)
    dosS3Storage(client, bucketname, results)
def getorcreatebucketandclient(region):
    client = genS3client(region)
    bucket = getExistingBucketName(client)
    if bucket is None:
        bucket = createBucket(client)
    return client, bucket
def genS3client(region=None):
    if region is None:
        return boto3.client('s3')
    else:
        return boto3.client('s3', region_name=region)
def getExistingBucketName(client):
    response = client.list_buckets()
    for bucket in response['buckets']:
        if s3_bucket_prefix in bucket['name']:
            return bucket['name']
    return None
def createBucket(client, region):
    bucket_name = genBucketName()
    if region is None:
        client.create_bucket(Bucket=bucket_name)
    else:
        location = {'locationconstraint': region}
        client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    return bucket_name
def genBucketName():
    return s3_bucket_prefix + str(uuid.uuid4())
def dosS3Storage(client, bucketname, results):
    data, data_hash = marshalResultsToObject(results)
    client.put_object(
        ACL='bucket-owner-full-control',
        Body=data,
        Bucket=bucketname,
        ContentEncoding='application/json',
        ContentMD5=data_hash,
        Key=file_name,
    )
def marshalResultsToObject(results):
    v2schema = {
        'schema': 2.0,
        'results': results,
    }
    data = json.dumps(v2schema)
    hash = hashlib.md5(str.encode(data))
    b64hash = base64.encode(hash.digest())
    return data, b64hash
def genFileKey():
    return time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())

if __name__ == '__main__':


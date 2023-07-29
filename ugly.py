#!/usr/bin/env python

# stdlib imports
import base64
import hashlib
import json
import os
import time
import uuid
# third party imports
import boto3
import requests

input_type = 'nfs'
scan_type = 'agent-pull'
max_agent_pull_retries = 10
nfs_read_dir = '/nfs/agent-output'
storage_type = 's3'
s3_region = 'eu-west-1'
s3_bucket_prefix = 'ip-scanner-results'
nfs_write_dir = '/nfs/ip-scanner-results'

def validateIP(maybe_ip):
    if not isinstance(maybe_ip, str):
        raise Exception('ip not a string: %s' % maybe_ip)
    parts = maybe_ip.split('.')
    if len(parts) != 4:
        raise Exception('ip not a dotted quad: %s' % maybe_ip)
    for num_s in parts:
        try:
            num = int(num_s)
        except ValueError:
            raise Exception('ip dotted-quad components not all integers: %s' % maybe_ip)
        if num < 0 or num > 255:
            raise Exception('ip dotted-quad component not between 0 and 255: %s' % maybe_ip)

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

if storage_type == 's3':
    storeResultsInS3(results, s3_region)
elif storage_type == 'nfs-write':
    file_name = time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())
    file_full_path = '/'.join([nfs_write_dir, file_name]) + '.json'
    v2schema = {
        'schema': 2.0,
        'results': results,
    }
    data = json.dumps(v2schema)
    with open(file_full_path, 'w') as fd:
        fd.write(data)
else:
    raise Exception('unrecognized storage_type %s' % storage_type)


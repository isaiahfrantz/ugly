'''
Ugly_lib contains methods used by ugly monitoring app
'''
class Ugly:
    # stdlib imports
    import base64
    import hashlib
    import json
    import os
    import time
    import uuid


    # TODO finish documenting methods
    # TODO write tests



    # Globals
    DEBUG = False

    # lib methods
    # app methods
    def validateIP(maybe_ip):
        '''
            Utility method to validate that ips have the correct form
                Parameters:
                    maybe_ip (string):
                        Exception if not string
                        Exception if not 4 octets
                        Exception if each part is not cast to int
                        Exception if each octet not between 0 and 255 inclusive
                Returns:
                    None
        '''
        if not isinstance(maybe_ip, str):
            raise Exception(f"ip not a string: {maybe_ip}")
        parts = maybe_ip.split('.')
        if len(parts) != 4:
            raise Exception(f"ip not a dotted quad: {maybe_ip}")
        for num_s in parts:
            try:
                num = int(num_s)
            except ValueError:
                raise Exception(f"ip dotted-quad components not all integers: {maybe_ip}")
            if num < 0 or num > 255:
                raise Exception(f"ip dotted-quad component not between 0 and 255: {maybe_ip}")





    def genFileKey():
        return time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())











class Nfs_client:
    def __init__(self):
        pass

    def nfs_write(results, nfs_write_dir):
        file_name = time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())
        file_full_path = f"{nfs_write_dir}/{file_name}.json"
        v2schema = {
            'schema': 2.0,
            'results': results,
        }
        data = json.dumps(v2schema)
        with open(file_full_path, 'w') as fd:
            fd.write(data)

    def open_target_file(file_path):
        with open(file_path) as fd:
            path_to_ip_lists = fd.read()
        ip_list = []
        for dir_name, subdir_list, file_list in os.walk(path_to_ip_lists):
            for file in file_list:
                with open(file) as fd:
                    data = json.load(fd)
                ip_list.extend(data['iplist'])
                for ip in ip_list:
                    validateIP(ip)
        return ip_list


    def nfs_read(ip_list, nfs_read_dir):
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
        return results

class S3_client:
    # third party imports
    import boto3
    import requests

    def __init__(self):
        pass

    def storeResultsInS3(results, region, s3_bucket_prefix):
        '''
            Wrapper to ensure client and bucket exist before passing results to be written to S3
                Parameters:
                    results (dict):
                        List of results to write out
                    region (string):
                        S3 region
                    s3_bucket_prefix (string):
                        S3 bucket prefix
                Returns:
                    None
        '''
        client, bucketname = getorcreatebucketandclient(region, s3_bucket_prefix)
        dosS3Storage(client, bucketname, results)

    def getorcreatebucketandclient(region, s3_bucket_prefix):
        '''
            Call methods to verify bucket exists ot create it
                Parameters:
                    region (string):
                        S3 region where bucket lives
                    s3_bucket_prefix (string):
                        S3 bucket prefix
                Returns: TODO verify the return types
                    client (?):
                        S3 Client object (?)
                    bucket (?):
                        S3 bucket id (?)
        '''
        client = genS3client(region)
        bucket = getExistingBucketName(client, s3_bucket_prefix)
        if bucket is None:
            bucket = createBucket(client)
        return client, bucket

    def genS3client(region=None):
        if region is None:
            return boto3.client('s3')
        else:
            return boto3.client('s3', region_name=region)

    def getExistingBucketName(client, s3_bucket_prefix):
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

    def agent_pull(ip_list, max_agent_pull_retries):
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
        return results

    def open_api(api_uri):
        response = requests.get(api_uri)
        if response.status_code != 200:
            raise Exception('non-200 status code: %d' % response.status_code)
        data = json.loads(response.text)
        ip_list = data['iplist']
        page_counter = 0
        while data['more'] is True:
            page_counter += 1
            response = requests.get(f"{api_uri}/?page=%d" % page_counter)
            if response.status_code != 200:
                raise Exception('non-200 status code: %d' % response.status_code)
            data = json.loads(response.text)
            ip_list.extend(data['iplist'])
        for ip in ip_list:
            validateIP(ip)
        return ip_list




'''
Ugly_lib contains methods used by ugly monitoring app
'''

# stdlib imports
import base64
import hashlib
import json
import os
import time
import uuid
import boto3
import requests
from abc import ABC, abstractmethod


class Ugly(ABC):
    # TODO finish documenting methods
    # TODO write tests

    # Class variables
    DEBUG = False

    @classmethod
    def ValidateIP(self, maybe_ip) -> None:
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
            raise ValueError(f"ip not a string: {maybe_ip}")
        parts = maybe_ip.split('.')
        if len(parts) != 4:
            raise ValueError(f"ip not a dotted quad: {maybe_ip}")
        for num_s in parts:
            try:
                num = int(num_s)
            except ValueError:
                raise ValueError(f"ip dotted-quad components not all integers: {maybe_ip}")
            if num < 0 or num > 255:
                raise ValueError(f"ip dotted-quad component not between 0 and 255: {maybe_ip}")

    @classmethod
    def GenFileKey():
        return time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())

    @classmethod
    def GetInputTypes() -> set:
        """Returns a set containing the currently allowed input_types"""
        return {'nfs','api'}

    def __init__(self, input_type, input_target, debug=False):
        self.input_type = input_type
        self.input_target = input_target
        # TODO: implement debug message output in the various functions
        Ugly.DEBUG = debug

    @property
    def input_type(self):
        """Return the input_type"""
        return self._input_type

    @input_type.setter
    def input_type(self, input_type):
        """Validate and set the input_type"""
        allowed_values = Ugly.GetInputTypes
        if not input_type in allowed_values:
            raise ValueError(f'Input_type ({input_type}) must be one of {allowed_values}')

        self._input_type = input_type

    @property
    def input_target(self):
        """Return the input_target"""
        return self._input_target

    @input_target.setter
    def input_target(self, input_target):
        """Validates and sets input_target"""
        # TODO: add validation
        self._input_target = input_target

    @abstractmethod
    def process(self):
        """This abstract method creates the requirement that descendant
            classes implement a process() appropriate to their io types
        """
        pass

class Nfs_client(Ugly):
    """Class to fetch and store data from/to NFS backing storage"""
    def __init__(self, input_target, read_dir, write_dir):
        super().__init__('nfs', input_target)
        self.read_dir = read_dir
        self.write_dir = write_dir

    @property
    def read_dir(self):
        """Return the nfs read_dir"""
        return self._read_dir

    @read_dir.setter
    def read_dir(self, read_dir):
        """Validates and sets nfs read_dir"""
        # TODO: add path, permissions, and space validation checks
        self._read_dir = read_dir

    @property
    def write_dir(self, write_dir):
        """Return the nfs write_dir"""
        # TODO: add path, permissions, and space validation checks
        self._write_dir = write_dir

    def nfs_write(self, results, write_dir):
        file_name = time.strftime('%y-%m-%d-%h:%m:%s', time.localtime())
        file_full_path = f"{write_dir}/{file_name}.json"
        v2schema = {
            'schema': 2.0,
            'results': results,
        }
        data = json.dumps(v2schema)
        with open(file_full_path, 'w') as fd:
            fd.write(data)

    def open_target_file(self, file_path):
        with open(file_path) as fd:
            path_to_ip_lists = fd.read()
        ip_list = []
        for dir_name, subdir_list, file_list in os.walk(path_to_ip_lists):
            for file in file_list:
                with open(file) as fd:
                    data = json.load(fd)
                ip_list.extend(data['iplist'])
                for ip in ip_list:
                    # TODO: handle exceptions here
                    Ugly.ValidateIP(ip)
        return ip_list

    def nfs_read(self, ip_list, nfs_read_dir):
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

    # implement abstract process() to do the work
    def process(self):
        """Process input and write out results to write_dir"""
        # TODO: add validation and testing
        ip_list = self.open_target_file(self.input_target)
        results = self.nfs_read(ip_list, self.read_dir)
        self.nfs_write(results, self.write_dir)

class S3_client(Ugly):
    """Class to fetch and store data from/to S3 backing storage"""
    def __init__(self, input_target, max_agent_pull_retries, region, bucket_prefix):
        super().__init__('api', input_target)
        self.max_agent_pull_retries = max_agent_pull_retries
        self.region = region
        self.bucket_prefix = bucket_prefix

    @property
    def max_agent_pull_retries(self):
        """Return the max_agent_pull_retries"""
        return self._max_agent_pull_retries

    @max_agent_pull_retries.setter
    def max_agent_pull_retries(self, max_agent_pull_retries):
        """Validates and sets max_agent_pull_retries"""
        self._max_agent_pull_retries = max_agent_pull_retries

    @property
    def region(self):
        """Return the region"""
        return self._region

    @region.setter
    def region(self, region):
        """Validates and sets region"""
        self._region = region

    @property
    def bucket_prefix(self):
        """Return the bucket_prefix"""
        return self._bucket_prefix

    @bucket_prefix.setter
    def bucket_prefix(self, bucket_prefix):
        """Validates and sets bucket_prefix"""
        self._bucket_prefix = bucket_prefix

    def storeResultsInS3(self, results, region, bucket_prefix):
        '''
            Wrapper to ensure client and bucket exist before passing results to be written to S3
                Parameters:
                    results (dict):
                        List of results to write out
                    region (string):
                        S3 region
                    bucket_prefix (string):
                        S3 bucket prefix
                Returns:
                    None
        '''
        client, bucketname = self.getorcreatebucketandclient(region, bucket_prefix)
        self.dosS3Storage(client, bucketname, results)

    def getorcreatebucketandclient(self, region, bucket_prefix):
        '''
            Call methods to verify bucket exists ot create it
                Parameters:
                    region (string):
                        S3 region where bucket lives
                    bucket_prefix (string):
                        S3 bucket prefix
                Returns: TODO verify the return types
                    client (?):
                        S3 Client object (?)
                    bucket (?):
                        S3 bucket id (?)
        '''
        client = self.genS3client(region)
        bucket = self.getExistingBucketName(client, bucket_prefix)
        if bucket is None:
            bucket = self.createBucket(client)
        return client, bucket

    def genS3client(self, region=None):
        if region is None:
            return boto3.client('s3')
        else:
            return boto3.client('s3', region_name=region)

    def getExistingBucketName(self, client, bucket_prefix):
        response = client.list_buckets()
        for bucket in response['buckets']:
            if bucket_prefix in bucket['name']:
                return bucket['name']
        return None

    def createBucket(self, client, region):
        bucket_name = S3_client.GenBucketName()
        if region is None:
            client.create_bucket(Bucket=bucket_name)
        else:
            location = {'locationconstraint': region}
            client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        return bucket_name

    def genBucketName(self):
        return self.bucket_prefix + str(uuid.uuid4())

    def dosS3Storage(self, client, bucketname, results):
        data, data_hash = self.marshalResultsToObject(results)
        client.put_object(
            ACL='bucket-owner-full-control',
            Body=data,
            Bucket=bucketname,
            ContentEncoding='application/json',
            ContentMD5=data_hash,
            Key=file_name, # TODO: where is this file_name coming from?
        )

    def marshalResultsToObject(self, results):
        v2schema = {
            'schema': 2.0,
            'results': results,
        }
        data = json.dumps(v2schema)
        hash = hashlib.md5(str.encode(data))
        b64hash = base64.encode(hash.digest())
        return data, b64hash

    def agent_pull(self, ip_list, max_agent_pull_retries):
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

    def open_api(self, api_uri):
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
            Ugly.ValidateIP(ip)
        return ip_list

    # implement abstract process()
    def process(self):
        """Process input and write out results to write_dir"""
        # TODO: add validation and testing
        ip_list = S3_client.open_api(self.input_target)
        results = S3_client.agent_pull(ip_list, self.max_agent_pull_retries)
        S3_client.storeResultsInS3(results, self.region, self.bucket_prefix)

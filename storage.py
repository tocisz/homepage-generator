import os
import shutil
import boto3
import botocore
import hashlib
from pathlib import Path

from config import config

class S3Storage:
    # Max size in bytes before uploading in parts.
    AWS_UPLOAD_MAX_SIZE = 20 * 1024 * 1024
    # Size of parts when uploading in parts
    AWS_UPLOAD_PART_SIZE = 6 * 1024 * 1024

    def __init__(self):
        if 'key' in config:
            self.s3 = boto3.client(
                's3',
                config['region'],
                aws_access_key_id = config['key'],
                aws_secret_access_key = config['secret']
            )
        else:
            self.s3 = boto3.client(
                's3',
                config['region']
            )

    def s3_etag(self, key):
        try:
            return self.s3.head_object(
                Bucket = config['bucket'],
                Key = key
            )['ETag'][1:-1]
        except botocore.exceptions.ClientError:
            return None

    # Purpose : Get the md5 hash of a file stored in S3
    # Returns : Returns the md5 hash that will match the ETag in S3
    def local_etag(self, sourcePath):
        filesize = os.path.getsize(sourcePath)
        hash = hashlib.md5()

        if filesize > S3Storage.AWS_UPLOAD_MAX_SIZE:

            block_count = 0
            md5string = ""
            with open(sourcePath, "rb") as f:
                for block in iter(lambda: f.read(S3Storage.AWS_UPLOAD_PART_SIZE), b""):
                    hash = hashlib.md5()
                    hash.update(block)
                    md5string = md5string + hash.digest()
                    block_count += 1

            hash = hashlib.md5()
            hash.update(md5string)
            return hash.hexdigest() + "-" + str(block_count)

        else:
            with open(sourcePath, "rb") as f:
                for block in iter(lambda: f.read(S3Storage.AWS_UPLOAD_PART_SIZE), b""):
                    hash.update(block)
            return hash.hexdigest()

    def upload_text(self, key, body):
        md5 = hashlib.md5(body.encode('utf-8')).hexdigest()
        etag = self.s3_etag(key)
        if key.endswith("rss.xml"):
            mimetype = 'application/rss+xml'
        else:
            mimetype = 'text/html'
        if md5 != etag:
            print("MD5: {}".format(md5))
            print("etag: {}".format(etag))
            self.s3.put_object(
                Bucket = config['bucket'],
                Key = key,
                Body = body,
                ACL = 'public-read',
                ContentType = mimetype
            )
            self.s3.put_object(
                Bucket = config['bucket'],
                Key = 't/' + key,
                ACL = 'public-read',
                WebsiteRedirectLocation = '/'+ key
            )
        else:
            print("Checksums match. Not uploading.")

    def upload_file(self, f, outdir):
        md5 = self.local_etag(f)
        if outdir == "":
            key = f.name
        else:
            key = outdir + '/' + f.name
        etag = self.s3_etag(key)
        if md5 != etag:
            print("MD5: {}".format(md5))
            print("etag: {}".format(etag))
            if f.suffix in config['suffix_to_type']:
                ct = config['suffix_to_type'][f.suffix]
            else:
                ct = 'application/octet-stream'
            print("Uploading as {}".format(ct))
            with f.open('rb') as fo:
                self.s3.put_object(
                    Bucket = config['bucket'],
                    Key = key,
                    Body = fo,
                    ACL = 'public-read',
                    ContentType = ct
                )
        else:
            print("Checksums match. Not uploading.")
        # shutil.copy(f, os.path.join(OUTPUT,f.name))

class FileStorage:
    def __init__(self):
        self.dir = config['out_dir']

    def upload_text(self, key, body):
        if '/' in key:
            d = '/'.join(key.split('/')[0:-1])
            p = os.path.join(self.dir, d)
            if not os.path.exists(p):
                os.makedirs(p)
        with open(os.path.join(self.dir, key), 'wb') as f:
            f.write(body.encode())

    def upload_file(self, f, outdir):
        p = os.path.join(self.dir, outdir)
        if not os.path.exists(p):
            os.makedirs(p)
        shutil.copy(f, os.path.join(p, f.name))

if __name__ == "__main__":
    # s = S3Storage()
    # s.upload_text("test", "test data")
    # s.upload_file(Path("storage.py"), "testdir")

    f = FileStorage()
    f.upload_text("test", "test data")
    f.upload_file(Path("storage.py"), "testdir")

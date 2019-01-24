import os
import shutil
from pathlib import Path
import re
import codecs
import markdown
from io import StringIO
import hashlib

import json
import boto3
import botocore

from dulwich import porcelain

DATA_DIR = "/tmp/data"
INPUT = "posts_source"
OUTPUT = "posts"
HEAD = "layouts/header.inc"
FOOT = "layouts/footer.inc"

with open(os.environ['LAMBDA_TASK_ROOT'] + '/config.json', 'r') as cf:
    config = json.load(cf)

s3 = boto3.client(
    's3',
    config['region'],
    # aws_access_key_id = config['key'],
    # aws_secret_access_key = config['secret']
)
#site = s3.Bucket(config['bucket'])

def title_from_path(input):
    return re.sub(r'.md$','', input.name).replace("-", " ")

def short_article_path(input):
    return re.sub(r'.md$','', input.name)

def s3_etag(key):
    try:
        return s3.head_object(
            Bucket = config['bucket'],
            Key = key
        )['ETag'][1:-1]
    except botocore.exceptions.ClientError:
        return None

# Max size in bytes before uploading in parts.
AWS_UPLOAD_MAX_SIZE = 20 * 1024 * 1024
# Size of parts when uploading in parts
AWS_UPLOAD_PART_SIZE = 6 * 1024 * 1024

# Purpose : Get the md5 hash of a file stored in S3
# Returns : Returns the md5 hash that will match the ETag in S3
def local_etag(sourcePath):
    filesize = os.path.getsize(sourcePath)
    hash = hashlib.md5()

    if filesize > AWS_UPLOAD_MAX_SIZE:

        block_count = 0
        md5string = ""
        with open(sourcePath, "rb") as f:
            for block in iter(lambda: f.read(AWS_UPLOAD_PART_SIZE), ""):
                hash = hashlib.md5()
                hash.update(block)
                md5string = md5string + hash.digest()
                block_count += 1

        hash = hashlib.md5()
        hash.update(md5string)
        return hash.hexdigest() + "-" + str(block_count)

    else:
        with open(sourcePath, "rb") as f:
            for block in iter(lambda: f.read(AWS_UPLOAD_PART_SIZE), b""):
                hash.update(block)
        return hash.hexdigest()

def upload_text(key, body):
    md5 = hashlib.md5(body.encode('utf-8')).hexdigest()
    etag = s3_etag(key)
    if md5 != etag:
        print("MD5: {}".format(md5))
        print("etag: {}".format(etag))
        s3.put_object(
            Bucket = config['bucket'],
            Key = key,
            Body = body,
            ACL = 'public-read',
            ContentType = 'text/html'
        )
        s3.put_object(
            Bucket = config['bucket'],
            Key = 't/' + key,
            ACL = 'public-read',
            WebsiteRedirectLocation = '/'+ key
        )
    else:
        print("Checksums match. Not uploading.")

def process(input, index, outdir):
    fout = short_article_path(input)
    title = title_from_path(input)
    text = input.open(mode="r", encoding="utf-8").read()
    html = markdown.markdown(
        text,
        extensions = ['extra','meta'],
        output_format="html5"
    )
    with StringIO() as output:
        output.write(
            codecs.open(
                HEAD,
                mode="r",
                encoding="utf-8"
            ).read().format(title=title)
        )
        output.write("""<div class="container-fluid">
  <div class="row">
    <div class="col-12 col-md-3 push-md-9 bd-sidebar">
""")
        output.write(index)
        output.write("""    </div>
    <div class="col-12 col-md-9 pull-md-3 bd-content">
""")
        output.write(html)
        output.write("""    </div>
  </div>
</div>
""")
        output.write(codecs.open(FOOT, mode="r", encoding="utf-8").read())
        body = output.getvalue()

    key = outdir + '/' + fout
    upload_text(key, body)

def upload_file(f, outdir):
    md5 = local_etag(f)
    etag = s3_etag(outdir + '/' + f.name)
    if md5 != etag:
        print("MD5: {}".format(md5))
        print("etag: {}".format(etag))
        if f.suffix in config['suffix_to_type']:
            ct = config['suffix_to_type'][f.suffix]
        else:
            ct = 'application/octet-stream'
        print("Uploading as {}".format(ct))
        with f.open('rb') as fo:
            s3.put_object(
                Bucket = config['bucket'],
                Key = outdir + '/' + f.name,
                Body = fo,
                ACL = 'public-read',
                ContentType = ct
            )
    else:
        print("Checksums match. Not uploading.")
    # shutil.copy(f, os.path.join(OUTPUT,f.name))

def upload_dir(dir, index, outdir=None):
    print("Going into {}".format(dir))
    if outdir is None:
        outdir = dir
    for f in Path(dir).glob("*"):
        if f.suffix == '.md':
            print("Processing {}".format(f.name))
            process(f, index, outdir)
        elif f.is_file():
            print("Uploading {}".format(f.name))
            upload_file(f, outdir)

def generate_index(posts, path_prefix=""):
    with StringIO() as output:
        output.write("<p>")
        if len(posts) > 0:
            output.write("<ul>")
        for f in posts:
            output.write("<li><a href=\"{path}\">{title}</a></li>".format(
                    path = path_prefix + short_article_path(f),
                    title = title_from_path(f)
                )
            )
        if len(posts) > 0:
            output.write("</ul>")
        output.write("</p>")
        return output.getvalue()

def generate_frontpage(posts):
    title = 'The blog archiv<span id="ref">e</span>';
    with StringIO() as output:
        output.write(
            codecs.open(
                HEAD,
                mode="r",
                encoding="utf-8"
            ).read().format(title=title)
        )
        output.write("""<div class="container-fluid">
<h1>{}</h1>""".format(title))
        output.write(generate_index(posts, OUTPUT+"/"))
        output.write("</div>")
        output.write("""<script type="text/javascript">
document.getElementById("ref").onclick = function() {
    document.location = "/refresh";
};
</script>
""")
        output.write(codecs.open(FOOT, mode="r", encoding="utf-8").read())
        return output.getvalue()

def checkout():
    if Path(DATA_DIR).is_dir():
        shutil.rmtree(DATA_DIR)
        porcelain.clone(config["git"], DATA_DIR)
        # porcelain.pull("data", config["git"])
    else:
        porcelain.clone(config["git"], DATA_DIR)

def main():
    print("Processing index.html")
    posts = [p for p in Path(INPUT).glob("*.md")]
    posts.sort()
    posts.reverse()
    index = generate_index(posts)
    front = generate_frontpage(posts)
    upload_text("index.html", front)
    
    upload_dir(INPUT, index, OUTPUT)
    upload_dir("css", index)
    upload_dir("404", index)

def success(msg):
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(msg)
    }

def error(msg):
    return {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(msg)
    }

def denied(msg):
    return {
        "isBase64Encoded": False,
        "statusCode": 403,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(msg)
    }

def lambda_handler(event, context):
    if event['body'] != '"ala ma kota"':
        return denied("Bad authentication string")
    try:
        os.chdir("/tmp")
        if "git" in config:
            checkout()
        os.chdir(DATA_DIR)
        main()
        return success('OK')
    except Exception as e:
        return error(getattr(e, 'message', repr(e)))

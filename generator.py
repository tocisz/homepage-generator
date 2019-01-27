import os
import shutil
from pathlib import Path
import re
import codecs
import markdown
from io import StringIO

import json

from dulwich import porcelain
from config import config

INPUT = "posts_source"
OUTPUT = "posts"
HEAD = "layouts/header.inc"
FOOT = "layouts/footer.inc"

from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader(os.path.join(config['data_dir'], 'templates')),
    autoescape=select_autoescape(['html', 'xml'])
)

def title_from_path(input):
    return re.sub(r'.md$','', input.name).replace("-", " ")

def short_article_path(input):
    path = re.sub(r'.md$','', input.name)
    if 'bucket' not in config:
        path += ".html"
    return path

import storage
if 'bucket' in config:
    storage = storage.S3Storage()
else:
    storage = storage.FileStorage()

def process(input, posts, outdir):
    fout = short_article_path(input)
    title = title_from_path(input)
    text = input.open(mode="r", encoding="utf-8").read()
    html = markdown.markdown(
        text,
        extensions = ['extra','meta'],
        output_format="html5"
    )
    body = env.get_template("post.html").render(
        title = title,
        cssdir = "../css",
        content = html,
        posts = [
            {
                "title" : title_from_path(p),
                "name" : short_article_path(p),
            } for p in posts
        ]
    )
    key = outdir + '/' + fout
    storage.upload_text(key, body)

def upload_dir(dir, posts = [], outdir=None):
    print("Going into {}".format(dir))
    if outdir is None:
        outdir = dir
    for f in Path(dir).glob("*"):
        if f.suffix == '.md':
            print("Processing {}".format(f.name))
            process(f, posts, outdir)
        elif f.is_file():
            print("Uploading {}".format(f.name))
            storage.upload_file(f, outdir)

def generate_index(posts):
    return env.get_template("index.html").render(
        title = "The blog archive",
        cssdir = "css",
        posts = [
            {
                "name" : short_article_path(p),
                "title" : title_from_path(p)
            } for p in posts
        ]
    )

def generate_refresh():
    return env.get_template("refresh.html").render(
        title = "Refresh page",
        cssdir = "css"
    )

def checkout():
    if Path(config['data_dir']).is_dir():
        shutil.rmtree(config['data_dir'])
        porcelain.clone(config["git"], config['data_dir'])
        # porcelain.pull(config['data_dir'], config["git"])
    else:
        porcelain.clone(config["git"], config['data_dir'])

def main():
    os.chdir(config['data_dir'])
    posts = [p for p in Path(INPUT).glob("*.md")]
    posts.sort()
    posts.reverse()

    storage.upload_text("index.html", generate_index(posts))
    storage.upload_text("refresh.html", generate_refresh())

    upload_dir(INPUT, posts, OUTPUT)
    upload_dir("css")
    upload_dir("404")

if __name__ == "__main__":
    main()

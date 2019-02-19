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
import stats

INPUT = "posts_source"
OUTPUT = "posts"

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

md = markdown.Markdown(
    extensions = ['extra','meta','codehilite'],
    output_format="html5"
)

import rss
rss = rss.Rss()

def process(input, posts, outdir):
    fout = short_article_path(input)
    title = title_from_path(input)
    text = input.open(mode="r", encoding="utf-8").read()
    html = md.convert(text)
    meta = md.Meta
    meta['title'] = title
    meta['url'] = fout
    if 'author' not in meta:
        meta['author'] = config['rss']['author']
    if 'date' in meta:
        meta['date'] = meta['date'][0]
    if 'abstract' in meta:
        meta['abstract'] = " ".join(meta['abstract'])
    body = env.get_template("post.html").render(
        title = title,
        cssdir = "../css",
        content = html,
        meta = meta,
        posts = [
            {
                "title" : title_from_path(p),
                "name" : short_article_path(p),
            } for p in posts
        ]
    )
    key = outdir + '/' + fout
    storage.upload_text(key, body, is_article = True)
    return meta

def upload_dir(dir, posts = [], outdir=None):
    print("Going into {}".format(dir))
    if outdir is None:
        outdir = dir
    for f in Path(dir).glob("*"):
        if f.suffix == '.md':
            print("Processing {}".format(f.name))
            rss.append(process(f, posts, outdir))
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

    ico = Path(config['data_dir']+"/favicon.ico")
    if ico.exists():
        print("Uploading favicon.ico")
        storage.upload_file(ico, "")

    if stats.articles_updated != 0:
        print("Uploading rss.xml")
        storage.upload_text("rss.xml", rss.generate())

if __name__ == "__main__":
    main()

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
    storage.upload_text(key, body)

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
            storage.upload_file(f, outdir)

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
    title_clean = re.sub(r"<.*?>", "", title)
    with StringIO() as output:
        output.write(
            codecs.open(
                HEAD,
                mode="r",
                encoding="utf-8"
            ).read().format(title=title_clean)
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
    if Path(config['data_dir']).is_dir():
        shutil.rmtree(config['data_dir'])
        porcelain.clone(config["git"], config['data_dir'])
        # porcelain.pull(config['data_dir'], config["git"])
    else:
        porcelain.clone(config["git"], config['data_dir'])

def main():
    os.chdir(config['data_dir'])
    print("Processing index.html")
    posts = [p for p in Path(INPUT).glob("*.md")]
    posts.sort()
    posts.reverse()
    index = generate_index(posts)
    front = generate_frontpage(posts)
    storage.upload_text("index.html", front)

    upload_dir(INPUT, index, OUTPUT)
    upload_dir("css", index)
    upload_dir("404", index)

if __name__ == "__main__":
    main()

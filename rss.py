from config import config
import datetime
from rfeed import *

def makeDate(s):
    a = s.split("-")
    return datetime.datetime(int(a[0]), int(a[1]), int(a[2]), 0, 0)

class Rss:
    def __init__(self):
        self.list = []

    def append(self, article):
        url = config['rss']['url'] + config['rss']['posts_dir'] + article['url']
        self.list.append(Item(
            title = article['title'],
            link = url,
            guid = Guid(url),
            author = article['author'],
            description = article['abstract'],
            pubDate = makeDate(article['date'])
        ))

    def generate(self):
        feed = Feed(
            title = config['rss']['title'],
            link = config['rss']['url'],
            description = config['rss']['description'],
            language = config['rss']['lang'],
            lastBuildDate = datetime.datetime.now(),
            items = self.list[::-1])
        return feed.rss()

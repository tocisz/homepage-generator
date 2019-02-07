articles_updated = 0
files_uploaded = 0

def article_updated():
    global articles_updated, files_uploaded
    articles_updated += 1
    files_uploaded += 1

def file_uploaded():
    global articles_updated, files_uploaded
    files_uploaded += 1

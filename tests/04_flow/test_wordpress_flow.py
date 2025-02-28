import time
from base64 import b64encode
import requests
import pytest
import lorem

### GLOBAL VARIABLES
EDITOR_USERNAME = 'editor'
EDITOR_PASSWORD = 'HWZg hZIP jEfK XCDE V9WM PQ3t'
COMMENTER_USERNAME = 'commenter'
COMMENTER_PASSWORD = 'SXlx hpon SR7k issV W2in zdTb'
BLOG_URL = 'https://gaworski.net'
POSTS_ENDPOINT_URL = BLOG_URL + "/wp-json/wp/v2/posts"
COMMENTS_ENDPOINT_URL = BLOG_URL + "/wp-json/wp/v2/comments"
TOKEN_EDITOR = b64encode(f"{EDITOR_USERNAME}:{EDITOR_PASSWORD}".encode('utf-8')).decode("ascii")
TOKEN_COMMENTER = b64encode(f"{COMMENTER_USERNAME}:{COMMENTER_PASSWORD}".encode('utf-8')).decode("ascii")


@pytest.fixture(scope='module')
def article():
    timestamp = int(time.time())
    article = {
        "article_creation_date": timestamp,
        "article_title": "This is new post " + str(timestamp),
        "article_subtitle": lorem.sentence(),
        "article_text": lorem.paragraph()
    }
    return article


@pytest.fixture(scope='module')
def editor_headers():
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + TOKEN_EDITOR
    }
    return headers


@pytest.fixture(scope='module')
def commenter_headers():
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + TOKEN_COMMENTER
    }
    return headers


@pytest.fixture(scope='module')
def posted_article(article, editor_headers):
    payload = {
        "title": article["article_title"],
        "excerpt": article["article_subtitle"],
        "content": article["article_text"],
        "status": "publish"
    }
    print(payload["title"])
    response = requests.post(url=POSTS_ENDPOINT_URL, headers=editor_headers, json=payload)
    return response


@pytest.fixture(scope='module')
def random_comment():
    return lorem.sentence()


@pytest.fixture(scope='module')
def posted_comment(posted_article, commenter_headers, random_comment):
    wordpress_post_id = posted_article.json()["id"]
    payload = {
        "post": wordpress_post_id,
        "content": random_comment
    }
    response = requests.post(url=COMMENTS_ENDPOINT_URL, headers=commenter_headers, json=payload)
    if response.status_code != 201:
        print("Failed to create comment:", response.status_code, response.text)
    return response


@pytest.fixture(scope='module')
def posted_reply(posted_comment, editor_headers, random_comment):
    wordpress_comment_id = posted_comment.json()["id"]
    payload = {
        "post": posted_comment.json()["post"],
        "content": random_comment,
        "parent": wordpress_comment_id
    }
    response = requests.post(url=COMMENTS_ENDPOINT_URL, headers=editor_headers, json=payload)
    return response


### CREATE ARTICLE
def test_new_post_is_successfully_created(posted_article):
    assert posted_article.status_code == 201
    assert posted_article.reason == "Created"
    assert posted_article.headers["Content-Type"] == "application/json; charset=UTF-8"


def test_new_created_post_can_be_read(posted_article, article):
    wordpress_post_id = posted_article.json()["id"]
    wordpress_post_url = f"{POSTS_ENDPOINT_URL}/{wordpress_post_id}"
    published_article = requests.get(url=wordpress_post_url)
    assert published_article.status_code == 200
    assert published_article.reason == "OK"
    wordpress_post_data = published_article.json()
    assert wordpress_post_data["title"]["rendered"] == article["article_title"]
    assert wordpress_post_data["excerpt"]["rendered"] == f'<p>{article["article_subtitle"]}</p>\n'
    assert wordpress_post_data["content"]["rendered"] == f'<p>{article["article_text"]}</p>\n'
    assert wordpress_post_data["status"] == "publish"


def test_article_is_publish_visible(posted_article):
    article_visibility = posted_article.json()
    assert article_visibility["status"] == "publish"


### CREATE COMMENT TO THE POST
def test_new_post_comment_is_successfully_created(posted_comment):
    assert posted_comment.status_code == 201
    assert posted_comment.reason == "Created"
    assert posted_comment.headers["Content-Type"] == "application/json; charset=UTF-8"


def test_new_comment_is_related_to_the_post(posted_comment, posted_article):
    wordpress_post_id = posted_article.json()["id"]
    wordpress_comment_id = posted_comment.json()["post"]
    assert wordpress_comment_id == wordpress_post_id


def test_new_comment_content(posted_comment, random_comment):
    wordpress_comment_data = posted_comment.json()
    assert wordpress_comment_data["content"]["rendered"] == f"<p>{random_comment}</p>\n"


def test_comment_is_approved_by_admin(posted_comment):
    comment_visibility = posted_comment.json()
    assert comment_visibility["status"] == "approved"


### CREATE REPLY TO COMMENT
def test_new_reply_is_successfully_created(posted_reply):
    assert posted_reply.status_code == 201
    assert posted_reply.reason == "Created"
    assert posted_reply.headers["Content-Type"] == "application/json; charset=UTF-8"


def test_new_reply_is_related_to_the_comment(posted_comment, posted_reply):
    wordpress_comment_id = posted_comment.json()["id"]
    wordpress_reply_parent_id = posted_reply.json()["parent"]
    assert wordpress_comment_id == wordpress_reply_parent_id


def test_new_reply_is_related_to_the_post(posted_article, posted_reply):
    wordpress_post_id = posted_article.json()["id"]
    wordpress_reply_post_id = posted_reply.json()["post"]
    assert wordpress_post_id == wordpress_reply_post_id


def test_reply_content(posted_reply, random_comment):
    wordpress_reply_data = posted_reply.json()
    assert wordpress_reply_data["content"]["rendered"] == f"<p>{random_comment}</p>\n"


def test_reply_is_approved_by_admin(posted_reply):
    reply_visibility = posted_reply.json()
    assert reply_visibility["status"] == "approved"

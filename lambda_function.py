#!/usr/bin/env python
# vim:fileencoding=utf-8

import os
import sys
import json
import datetime
import pytz
import requests
import boto3
import feedparser
from bs4 import BeautifulSoup

SERVICES = {
        "conoha_wing": {
            "executor": "bs4",
            "news_url": "https://www.conoha.jp/wing/news/",
            "base_url": "https://www.conoha.jp",
            "s3_key": "conoha_wing_news.json",
            "selector": "main > section.section.news > div > ul > li.listNews_item"
        },
        "muumuu_news": {
            "executor": "bs4",
            "news_url": "https://muumuu-domain.com/information/news",
            "base_url": "https://muumuu-domain.com",
            "s3_key": "muumuu-domain_news.json",
            "selector": "main > div.muu-column-container > div > section"
        },
        "muumuu_campaign": {
            "executor": "bs4",
            "news_url": "https://muumuu-domain.com/information/campaigns",
            "base_url": "https://muumuu-domain.com",
            "s3_key": "muumuu-domain_campaign.json",
            "selector": "main > div.muu-column-container > div > section"
        },
        "xserver": {
            "executor": "bs4",
            "news_url": "https://www.xserver.ne.jp/support/news.php",
            "base_url": "https://www.xserver.ne.jp",
            "s3_key": "xserver_news.json",
            "selector": "#toggle-target > div.contents > section > section > div > dl"
        },
        "xserver_business": {
            "executor": "bs4",
            "base_url": "https://business.xserver.ne.jp",
            "news_url": "https://business.xserver.ne.jp/news/",
            "s3_key": "xserver_business_news.json",
            "selector": "#main > section > div > section > div > dl"
        },
        "xserver_ssl": {
            "executor": "bs4",
            "base_url": "https://ssl.xdomain.ne.jp",
            "news_url": "https://ssl.xdomain.ne.jp/news/",
            "s3_key": "xserver_ssl_news.json",
            "selector": "main > section > div > article > ul > li"
        },
        "xdomain": {
            "executor": "bs4",
            "base_url": "https://www.xdomain.ne.jp",
            "news_url": "https://www.xdomain.ne.jp/support/news.php",
            "s3_key": "xdomain_news.json",
            "selector": "main > section > div > article > ul > li"
        },
        "lolipop": {
            "executor": "bs4",
            "base_url": "https://lolipop.jp",
            "news_url": "https://lolipop.jp/info/news/",
            "s3_key": "lolipop_news.json",
            "selector": "main > div > div.main-body > section > div > div > ul > li.lol-info-contents__item"
        },
        "lolipop_campaign": {
            "executor": "bs4",
            "news_url": "https://lolipop.jp/info/campaign/",
            "base_url": "https://lolipop.jp",
            "s3_key": "lolipop_campaign.json",
            "selector": "main > div > div.main-body > section > div > div > ul > li.lol-info-contents__item"
        },
        "sakura_news": {
            "executor": "feedparser",
            "news_url": "https://www.sakura.ad.jp/corporate/information/newsreleases/feed/",
            "s3_key": "sakura_news.json",
            "tags": [ "さくらのレンタルサーバ", "さくらのマネージドサーバ" ]
        },
        "sakura_announcement": {
            "executor": "feedparser",
            "news_url": "https://www.sakura.ad.jp/corporate/information/announcements/feed/",
            "s3_key": "sakura_announcement.json",
            "tags": [ "さくらのレンタルサーバ", "さくらのマネージドサーバ" ]
        },
        "mixhost_news": {
            "executor": "feedparser",
            "news_url": "https://mixhost.jp/news/feed",
            "s3_key": "mixhost_news.json",
            "tags": [ "お知らせ" ]
        },
        "onamae_news": {
            "executor": "feedparser",
            "news_url": "https://www.onamae.com/news/rss/domain/",
            "s3_key": "onamae_news.json",
            "tags": []
        }
 
    }

SLACK_MESSAGE = "{date} <{url}|{title}>"

def conv_time_struct_time_to_datetime(struct_time):

    tz = pytz.timezone("Asia/Tokyo")
    return datetime.datetime(*struct_time[:6], tzinfo=pytz.utc).astimezone(tz)

def conv_str_to_datetime(s):
    # 'Wed, 24 May 2023 00:00:00 +0900'
    return datetime.datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z")

def exists_states(check_data, states):

    for data in states:
        if check_data["date"] == data["date"] and check_data["url"] == data["url"] and check_data["title"] == data["title"]:
            return True

    return False


def exists_feed_tags(tags, check_tags):

    if type(check_tags).__name__ != "list":
        return False

    for check_tag in check_tags:
        for tag in tags:
            if tag["term"] == check_tag:
                return True

    return False


def get_states(s3, **kwargs):

    response = s3.list_objects_v2(Bucket=kwargs["bucket"])
    for content in response["Contents"]:
        if content["Key"] != kwargs["key"]:
            continue
        else:
            binary = s3.get_object(Bucket=kwargs["bucket"], Key=kwargs["key"])["Body"].read()
            return json.loads(binary.decode("utf-8"))

    return []


def send_to_slack(service, notifications):

    if len(notifications) == 0:
        return

    headers = { "Content-Type": "application/json; charset=UTF-8" }

    blocks = [ { "type": "section", "text": { "type": "mrkdwn", "text": "[{0}] ".format(service) + SLACK_MESSAGE.format(**data) } } for data in notifications ]
    payload = {
        "unfurl_links": True,
        "username":     "hosting news bot",
        "icon_emoji":   ":slack:",
        "blocks":       blocks
        }
    res = requests.post(os.environ["SLACK_WEBHOOK_URL"], data=json.dumps(payload), headers=headers)
    if res.status_code == 200:
        return True
    else:
        res.raise_for_status()


def get_news_by_bs4(news_url, **kwargs):

    res = requests.get(news_url)
    soup = BeautifulSoup(res.text, "html.parser")
    elems = soup.select(kwargs["selector"])
    news  = []
    for elem in elems:

        date  = None
        title = None
        url   = None
        data  = None
        if kwargs["service"] == "conoha_wing":
            date  = elem.find("div", class_="listNewsUnit_date").text.strip()
            title = elem.find("span", class_="textLink has-arrow textColor-inherit has-noHover").text.strip()
            href  = elem.find("a", class_="listNewsUnit").get("href")
            url   = kwargs["base_url"] + href

        elif kwargs["service"] == "muumuu_news" or kwargs["service"] == "muumuu_campaign" :
            # date
            p = elem.find("p", class_="muu-section__date")
            if p is None:
                continue
            date = p.text
            # title
            title = elem.find("h3", class_="muu-infomation__title").text
            # url
            href = elem.find("a", class_="muu-button muu-button--primary").get("href")
            url  = kwargs["base_url"] + href

        elif kwargs["service"] == "xserver" or kwargs["service"] == "xserver_business" :
            # date
            date = elem.dt.text
            elems2 = elem.find_all("a")
            for elem2 in elems2:
                href  = elem2.get("href")
                url   = kwargs["base_url"] + href.replace("..", "") if kwargs["service"] == "xserver" else news_url + href
                title = elem2.text
        elif kwargs["service"] == "xdomain" or kwargs["service"] == "xserver_ssl" :
            date = elem.find("span", class_="date century").text
            a = elem.find("a", class_="hover-opacity")
            title = a.text.strip()
            url   = a.get("href")

        elif kwargs["service"] == "lolipop" or kwargs["service"] == "lolipop_campaign" :
            date = elem.find("time", class_="lol-info-list__date").text.strip()
            title = elem.find("span", class_="lol-info-item__title").text.strip()
            a = elem.select("p.lol-info-accordion-panel__link > a")[-1]
            url  = kwargs["base_url"] + a.get("href")

        data = {"date": date, "url": url, "title": title}
        news.append(data)

    return news

def get_news_by_feedparser(news_url, **kwargs):

    atom = feedparser.parse(news_url)
    news  = []

    for entry in atom["entries"]:

        if "tags" in entry:
            if type(kwargs["tags"]).__name__ == "list" and  not exists_feed_tags(entry["tags"], kwargs["tags"]):
                continue

        title  = entry["title"]
        url    = entry["link"]

        if "published_parsed" in entry :
            dt    = conv_time_struct_time_to_datetime(entry["published_parsed"])
        elif "updated" in entry:
            dt = conv_str_to_datetime(entry["updated"])

        date  = dt.strftime("%Y-%m-%d")
        data = {"date": date, "url": url, "title": title}
        news.append(data)

    return news


def lambda_handler(event, context):

    s3     = boto3.client("s3")
    bucket = os.environ["S3_BUCKET"]
    body   = {}

    for service in SERVICES.keys():

        print("{0} parser start".format(service))

        key      = SERVICES[service]["s3_key"]
        news_url = SERVICES[service]["news_url"]
        executor = SERVICES[service]["executor"]
        base_url = SERVICES[service]["base_url"] if "base_url" in SERVICES[service] else None
        selector = SERVICES[service]["selector"] if "selector" in SERVICES[service] else None
        tags     = SERVICES[service]["tags"] if "tags" in SERVICES[service] else None

        news = []
        notifications = []

        # download state json
        states = get_states(s3, bucket=bucket, key=key)

        if executor == "bs4":
            news = get_news_by_bs4(news_url, service=service, selector=selector, base_url=base_url)
        elif executor == "feedparser":
            news = get_news_by_feedparser(news_url, service=service, tags=tags)

        for data in news:
            if not exists_states(data, states):
                print(service + " news update. date:{date} url:{url} title:{title}".format(**data))
                notifications.append(data)

        # send to slack
        count = len(notifications)
        if count > 0 and "SLACK_WEBHOOK_URL" in os.environ:
           send_to_slack(service, notifications)
           #pass
        else:
           print("{0} skip slack notification.".format(service))

        # save
        json_string = json.dumps(news, sort_keys=True, indent=2, ensure_ascii=False)
        s3.put_object(Body=json_string.encode("utf-8"), Bucket=bucket, Key=key)

        body[service] = { "update": count }

        print("{0} parser end".format(service))

    return {
        'statusCode': 200,
        'body': body
    }

if __name__ == '__main__':
    if os.path.exists("event.json"):
        event = json.load(open("event.json", "r"))
    else:
        event = {}
    context = {}
    res = lambda_handler(event, context)
    print(res)

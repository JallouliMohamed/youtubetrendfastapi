from typing import Optional
import requests, sys, time, os, argparse
from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
import uvicorn

import pandas as pd
import json


class Item(BaseModel):
    country: str


unsafe_characters = ['\n', '"']
snippet_features = ["title",
                    "publishedAt",
                    "channelId",
                    "channelTitle",
                    "categoryId"]

header = ["video_id"] + snippet_features + ["trending_date", "tags", "view_count", "likes", "dislikes",
                                            "comment_count", "thumbnail_link", "comments_disabled",
                                            "ratings_disabled", "description"]


def prepare_feature(feature):
    for ch in unsafe_characters:
        feature = str(feature).replace(ch, "")
    return f'"{feature}"'


def api_request(page_token, country_code):
    request_url = f"https://www.googleapis.com/youtube/v3/videos?part=id,statistics,snippet{page_token}chart=mostPopular&regionCode={country_code}&maxResults=50&key={api_key}"
    print(request_url)
    request = requests.get(request_url)
    if request.status_code == 429:
        print("Temp-Banned due to excess requests, please wait and continue later")
        sys.exit()
    return request.json()


def get_tags(tags_list):
    return prepare_feature("|".join(tags_list))


def get_videos(items):
    lines = []
    listvideos = []
    for video in items:
        comments_disabled = False
        ratings_disabled = False

        ''' We can assume something is wrong with the video if it has no statistics, often this means it has been deleted
         so we can just skip it'''
        if "statistics" not in video:
            continue

        # A full explanation of all of these features can be found on the GitHub page for this project
        video_id = prepare_feature(video['id'])

        # Snippet and statistics are sub-dicts of video, containing the most useful info
        snippet = video['snippet']
        statistics = video['statistics']
        print(video.keys())
        if 'likeCount' in statistics and 'dislikeCount' in statistics:
            likes = statistics['likeCount']
            dislikes = statistics['dislikeCount']
        else:
            ratings_disabled = True
            likes = 0
            dislikes = 0

        if 'commentCount' in statistics:
            comment_count = statistics['commentCount']
        else:
            comments_disabled = True
            comment_count = 0
        listvideos.append({'videoid': prepare_feature(video['id']), 'view_count': statistics.get("viewCount", 0),'likes':likes,'dislikes':dislikes,
                           'comment_count':comment_count,
                           'description': snippet.get("description", ""),
                           'thumbnail_link': snippet.get("thumbnails", dict()).get("default", dict()).get("url", ""),
                           'trending_time': time.strftime("%y.%d.%m"),
                           'tags': get_tags(snippet.get("tags", ["[none]"]))})
        # This list contains all of the features in snippet that are 1 deep and require no special processing

        '''This may be unclear, essentially the way the API works is that if a video has comments or ratings disabled
       then it has no feature for it, thus if they don't exist in the statistics dict we know they are disabled'''

    return listvideos


def get_pages(country_code, next_page_token="&"):
    country_data = []

    # Because the API uses page tokens (which are literally just the same function of numbers everywhere) it is much
    # more inconvenient to iterate over pages, but that is what is done here.
    while next_page_token is not None:
        # A page of data i.e. a list of videos and all needed data
        video_data_page = api_request(next_page_token, country_code)

        # Get the next page token and build a string which can be injected into the request with it, unless it's None,
        # then let the whole thing be None so that the loop ends after this cycle
        next_page_token = video_data_page.get("nextPageToken", None)
        next_page_token = f"&pageToken={next_page_token}&" if next_page_token is not None else next_page_token

        # Get all of the items as a list and let get_videos return the needed features
        items = video_data_page.get('items', [])
        country_data += get_videos(items)
    return country_data


def get_pages_to_df(country_code, next_page_token="&"):
    country_data = []

    # Because the API uses page tokens (which are literally just the same function of numbers everywhere) it is much
    # more inconvenient to iterate over pages, but that is what is done here.
    while next_page_token is not None:
        # A page of data i.e. a list of videos and all needed data
        video_data_page = api_request(next_page_token, country_code)

        # Get the next page token and build a string which can be injected into the request with it, unless it's None,
        # then let the whole thing be None so that the loop ends after this cycle
        next_page_token = video_data_page.get("nextPageToken", None)
        next_page_token = f"&pageToken={next_page_token}&" if next_page_token is not None else next_page_token

        # Get all of the items as a list and let get_videos return the needed features
        items = video_data_page.get('items', [])
        country_data += get_videos(items)
    print(country_data)
    return country_data


def setup(api_path, code_path):
    with open(api_path, 'r') as file:
        api_key = file.readline()

    with open(code_path) as file:
        country_codes = [x.rstrip() for x in file]

    return api_key, country_codes


api_key, country_codes = setup("app/api_key.txt", "app/country_codes.txt")
output_dir = "../output/"

app = FastAPI()


@app.get("/youtubeapi")
def read_root(item: Item):
    df = pd.DataFrame(get_pages(item.country))
    collection = MongoClient('172.18.0.2:27017')['youtubedata']['trend' + item.country]
    records = df.to_dict(orient='records')
    collection.insert_many(records)
    return get_pages(item.country)


'''@app.post("/items/")
def read_item(item: Item):
    
    return item '''
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)

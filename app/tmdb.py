from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import re
from collections import OrderedDict

import urllib
import requests


API_KEY = "0d77f2a9250ff38a3a22ecb9e20d7a74"
ROOT_URL = "https://api.themoviedb.org/3/search"


def fuzzy_search(search_term, search_list, score_cutoff = 70):
    results = process.extract(search_term, search_list, limit=8)
    return [r for r in results if r[1] >= score_cutoff]


def remove_duplicates(input_list):
    unique_dict = OrderedDict.fromkeys(input_list)
    return list(unique_dict.keys())


def search(query):
    query = re.sub(r'[^\w\s]', '',query)
    tvresponse = requests.get(f"{ROOT_URL}/tv?api_key={API_KEY}&query=" + urllib.parse.quote(query) ).json()["results"]
    movieresponse = requests.get(f"{ROOT_URL}/movie?api_key={API_KEY}&query=" + urllib.parse.quote(query) ).json()["results"]
    relevant = []
    clean_title = lambda r: re.sub(r'[^\w\s\'-]', '', ((r.get("name") or r.get("title"))).lower())
    scores = {clean_title(r): r["popularity"] for r in tvresponse + movieresponse}
    results = remove_duplicates([clean_title(r) for r in tvresponse + movieresponse])

    def sortfun(el):
        return -scores[el[0]]*scores[el[0]]*el[1]

    return [r[0] for r in sorted(fuzzy_search(query, results), key=sortfun)]

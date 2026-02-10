# VERSION: 1.9
# AUTHORS: Lyra Aranha (lyra@lazulyra.com) - Fixed for compatibility
# CONTRIBUTORS: AliAl-ojeely - Fixed syntax for Python 3.10+ compatibility

import dataclasses
import json
import re
from urllib.parse import urlencode, unquote
from typing import List, Optional, Union, Dict, Any
from helpers import retrieve_url
from novaprinter import prettyPrinter

@dataclasses.dataclass
class yts_torrent:
    url: str
    hash: str
    quality: str
    type: str
    is_repack: str
    video_codec: str
    bit_depth: str
    audio_channels: str
    seeds: int
    peers: int
    size: str
    size_bytes: int
    date_uploaded: str
    date_uploaded_unix: int

@dataclasses.dataclass
class yts_movie:
    id: int
    url: str
    imdb_code: str
    title: str
    title_english: str
    title_long: str
    slug: str
    year: int
    genres: List[str]
    language: str
    background_image: str
    background_image_original: str
    small_cover_image: str
    medium_cover_image: str
    large_cover_image: str
    state: str
    torrents: List[yts_torrent]
    date_uploaded: str
    date_uploaded_unix: int

    def __post_init__(self):
        # Safety check if torrents is None or empty
        if not self.torrents:
            self.torrents = []
        else:
            self.torrents = list(yts_torrent(**torrent) for torrent in self.torrents)

@dataclasses.dataclass
class yts_data:
    movie_count: int
    limit: int
    page_number: int
    movies: Optional[List[yts_movie]] = None

    def __post_init__(self):
        if self.movies:
            self.movies = list(yts_movie(**movie) for movie in self.movies)

@dataclasses.dataclass
class yts_response:
    status: str
    status_message: str
    data: yts_data

    def __post_init__(self):
        # Check if data is a dictionary before unpacking
        if isinstance(self.data, dict):
            self.data = yts_data(**self.data)

class yts(object):
    """
    `url`, `name`, `supported_categories` should be static variables of the engine_name class,
    otherwise qbt won't install the plugin.
    """
    url = "https://yts.bz/"
    api_url = "https://yts.bz/api/v2/list_movies.json?"
    name = "YTS"
    supported_categories = {"all": "0", "movies": "1"}

    def search(self, what: str, cat: str = "all"):
        search_url = self.api_url
        what = unquote(what)
        search_params = {}

        # quality tagging
        quality_rstring = r"(?:quality=)?((?:2160|1440|1080|720|480|240)p|3D)"
        quality_re = re.search(quality_rstring, what)
        search_resolution = None
        if quality_re:
            search_resolution = quality_re.group(1)
            search_params["quality"] = search_resolution
            what = re.sub(quality_rstring, "", what).strip()
        
        # codec tagging
        codec_rstring = r"\.?(?:x|h)(264|265)"
        codec_re = re.search(codec_rstring, what)
        search_codec = None
        if codec_re:
            search_codec = "x" + codec_re.group(1)
            if "quality" in search_params:
                search_params["quality"] += f".{search_codec}"
            what = re.sub(codec_rstring, "", what).strip()

        # rating tagging
        rating_rstring = r"(?:min(?:imum)?_)?rating=(\d)"
        rating_re = re.search(rating_rstring, what)
        if rating_re:
            min_rating = rating_re.group(1)
            search_params["minimum_rating"] = min_rating
            what = re.sub(rating_rstring, "", what).strip()

        # genre tagging
        genre_rstring = r"genre=(\w+)"
        genre_re = re.search(genre_rstring, what)
        if genre_re:
            genre = genre_re.group(1)
            what = re.sub(genre_rstring, "", what).strip()
            search_params["genre"] = genre

        # clean up extra params
        search_rstring = r"&page=\d+"
        what = re.sub(search_rstring, "", what).strip()

        # finalize url
        if what:
            search_params["query_term"] = what
        
        search_url += urlencode(search_params)

        try:
            response_text = retrieve_url(search_url)
            response_json = json.loads(response_text)
            api_result = self.convert_response(response_json)
        except Exception as e:
            # print(f"Error parsing YTS response: {e}")
            return

        if api_result.status != "ok":
            return
        
        if not api_result.data or not api_result.data.movies:
            return

        # Display first page results immediately
        self.process_movies(api_result.data.movies, search_codec, search_resolution)

    def process_movies(self, movies, search_codec, search_resolution):
        if not movies:
            return

        for movie in movies:
            if not movie.torrents:
                continue
                
            for torrent in movie.torrents:
                if search_codec and torrent.video_codec != search_codec:
                    continue
                if search_resolution and torrent.quality != search_resolution:
                    continue
                
                formatTorrent = {
                    "link": torrent.url,
                    "name": f"{movie.title_long} [{torrent.quality}] [{torrent.video_codec}] [{torrent.type}] [YTS]",
                    "size": torrent.size,
                    "seeds": str(torrent.seeds),
                    "leech": str(torrent.peers),
                    "engine_url": self.url,
                    "desc_link": movie.url,
                    "pub_date": torrent.date_uploaded_unix,
                }
                prettyPrinter(formatTorrent)

    def convert_response(self, api_response: dict) -> yts_response:
        # Filter keys to match dataclass fields to avoid errors with extra API fields
        valid_keys = {f.name for f in dataclasses.fields(yts_response)}
        filtered_args = {k: v for k, v in api_response.items() if k in valid_keys}
        return yts_response(**filtered_args)

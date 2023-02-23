import os
import sys

import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import config
import discord
import spotipy
import spotipy.util as util
import logging
from spotipy.oauth2 import SpotifyOAuth
from recursiveJson import extract_values
from urllib import parse

scopes = ["https://www.googleapis.com/auth/youtube"]

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "gcp-client-secret.json"

spotify_auth_manager = SpotifyOAuth(config.spotify_client_id, config.spotify_secret,
                                    redirect_uri=config.sp_redirect_uri, scope=config.sp_scope, username='1234656043')
sp = spotipy.Spotify(auth_manager=spotify_auth_manager)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

yt_playlist_id = config.youtube_playlist_id
sp_playlist_id = config.sp_playlist_id
if config.dev:
    logging.info("Dev mode enabled")
    yt_playlist_id = config.dev_youtube_playlist_id
    sp_playlist_id = config.dev_sp_playlist_id


def get_authenticated_service():
    if os.path.exists("CREDENTIALS_PICKLE_FILE"):
        with open("CREDENTIALS_PICKLE_FILE", 'rb') as f:
            credentials = pickle.load(f)
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_local_server()
        with open("CREDENTIALS_PICKLE_FILE", 'wb') as f:
            pickle.dump(credentials, f)
    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)


youtube = get_authenticated_service()


def get_youtube_video_data_by_artist_and_track(artist_name, track_name):
    searchRequest = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=f"{artist_name} {track_name}",
    )

    return searchRequest.execute()


def get_youtube_video_data_by_id(id):
    searchRequest = youtube.videos().list(part="snippet", id=id)

    return searchRequest.execute()


def get_video_id(yt_data):
    return yt_data['items'][0]['id']['videoId']


def create_video_link(yt_video_id):
    return f"https://www.youtube.com/watch?v={yt_video_id}"


def get_existing_videos_in_playlist(playlist_id):
    playlistQuery = youtube.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=50,
        playlistId=playlist_id
    )
    return playlistQuery.execute()


def add_video_to_youtube_playlist(yt_video_id):
    logging.info('Adding %s to playlist', yt_video_id)
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": yt_playlist_id,
                "position": 0,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": f"{yt_video_id}"
                }
            }
        }
    ).execute()


@client.event
async def on_ready():
    logging.info('We have logged in as %s', client.user)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    sp_trigger_string = 'https://open.spotify.com'
    yt_trigger_strings = ['https://www.youtube.com/watch',
                          'https://music.youtube.com/watch']
    if sp_trigger_string in message.content:
        logging.info('Triggered spotify flow with message %s', message.content)
        track_data = sp.track(message.content)
        logging.info('got spotify track data')
        track_uri = track_data['uri']
        logging.info('got spotify track uri %s', track_uri)
        sp_artistname = track_data['artists'][0]['name']
        sp_trackname = track_data['name']
        logging.info('got spotify artist %s and track %s',
                     sp_artistname, sp_trackname)
        await add_to_sp_playlist(message, track_uri)

        await message.channel.send('Looking it up on YouTube...')
        try:
            yt_data = get_youtube_video_data_by_artist_and_track(
                sp_artistname, sp_trackname)
            if not yt_data:
                await message.channel.send("Sorry. I couldn't find anything")
            else:
                yt_id = get_video_id(yt_data)
                yt_link = create_video_link(yt_id)
                await message.channel.send(f"{yt_link}")
                await try_add_yt_playlist(message, yt_id)
        except Exception as e:
            await message.channel.send("something went wrong. I don't care")
            logging.error('Error getting YouTube data: %o', e)
    for yt_trigger in yt_trigger_strings:
        if (yt_trigger in message.content):
            logging.info('%s triggered youtube flow', message.content)
            url_parsed = parse.urlparse(message.content)
            qsl = parse.parse_qs(url_parsed.query)
            yt_id = qsl['v'][0]
            logging.info('parsed %s from message', yt_id)
            await try_add_yt_playlist(message, yt_id=yt_id)
            video_data = get_youtube_video_data_by_id(yt_id)
            title = video_data['items'][0]['snippet']['title']
            await message.channel.send('Looking it up on Spotify...')
            logging.info('looking up "%s" on spotify', title)
            sp_results = sp.search(q=title, type='track')
            if not sp_results:
                await message.channel.send("Sorry. I couldn't find anything")
            else:
                track = sp_results['tracks']['items'][0]
                sp_link = track['external_urls']['spotify']
                sp_uri = track['uri']
                await message.channel.send(f"{sp_link}")
                await add_to_sp_playlist(message, sp_uri)


async def try_add_yt_playlist(message, yt_id):
    try:
        existingVideos = get_existing_videos_in_playlist(
            yt_playlist_id)
        existingVideoIds = extract_values(existingVideos, "videoId")
        if (yt_id not in existingVideoIds):
            try:
                add_video_to_youtube_playlist(yt_id)
                await message.channel.send(f"Added video to YouTube playlist")
            except Exception as e:
                logging.error("exception when inserting into playlist: %o", e)
        else:
            await message.channel.send("Video already exists in YouTube playlist")
    except Exception as e:
        logging.error('couldnt add track to youtube %o', e)


async def add_to_sp_playlist(message, track_uri):
    try:
        current_sp_tracks = sp.user_playlist_tracks(
            config.sp_username, sp_playlist_id)
        current_sp_track_uris = extract_values(current_sp_tracks, 'uri')
        if track_uri not in current_sp_track_uris:
            sp.user_playlist_add_tracks(
                config.sp_username, sp_playlist_id, [track_uri])
            await message.channel.send("Added track to Spotify playlist")
        else:
            await message.channel.send("Track already exists in Spotify playlist")
    except Exception as e:
        logging.error('couldnt add track to spotify %o', e)

client.run(config.botToken)

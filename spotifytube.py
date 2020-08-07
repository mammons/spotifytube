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
from spotipy.oauth2 import SpotifyOAuth
from recursiveJson import extract_values

scopes = ["https://www.googleapis.com/auth/youtube"]

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "client_secret_862974823303-5k6td646glkbegi3j4bq83ns87q2a17g.apps.googleusercontent.com.json"

spotify_auth_manager = SpotifyOAuth(config.spotify_client_id, config.spotify_secret, redirect_uri=config.sp_redirect_uri, scope=config.sp_scope, username='1234656043')
sp = spotipy.Spotify(auth_manager=spotify_auth_manager)

client = discord.Client()


def get_authenticated_service():
    if os.path.exists("CREDENTIALS_PICKLE_FILE"):
        with open("CREDENTIALS_PICKLE_FILE", 'rb') as f:
            credentials = pickle.load(f)
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        with open("CREDENTIALS_PICKLE_FILE", 'wb') as f:
            pickle.dump(credentials, f)
    return googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)


youtube = get_authenticated_service()


def get_youtube_video_data(artist_name, track_name):
    searchRequest = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=f"{artist_name} {track_name}",
    )

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
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": config.youtube_playlist_id,
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
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    trigger_string = 'https://open.spotify.com'
    if trigger_string in message.content:

        track_data = sp.track(message.content)
        track_uri = track_data['uri']
        sp_artistname = track_data['artists'][0]['name']
        sp_trackname = track_data['name']

        try:
            current_sp_tracks = sp.user_playlist_tracks(
                config.sp_username, config.sp_playlist_id)
            current_sp_track_uris = extract_values(current_sp_tracks, 'uri')
            if track_uri not in current_sp_track_uris:
                sp.user_playlist_add_tracks(
                    config.sp_username, config.sp_playlist_id, [track_uri])
                await message.channel.send("Added track to Spotify playlist")
            else:
                await message.channel.send("Track already exists in Spotify playlist")
        except Exception as e:
            print(f'couldnt add track to spotify {e}')

        await message.channel.send('Looking it up on YouTube...')
        try:
            yt_data = get_youtube_video_data(sp_artistname, sp_trackname)
            if not yt_data:
                await message.channel.send("Sorry. I couldn't find anything")
            else:
                yt_id = get_video_id(yt_data)
                yt_link = create_video_link(yt_id)
                await message.channel.send(f"{yt_link}")
                existingVideos = get_existing_videos_in_playlist(
                    config.youtube_playlist_id)
                existingVideoIds = extract_values(existingVideos, "videoId")
                if(yt_id not in existingVideoIds):
                    try:
                        add_video_to_youtube_playlist(yt_id)
                        await message.channel.send(f"Added video to YouTube playlist")
                    except Exception as e:
                        print(f"exception when inserting into playlist: {e}")
                else:
                    await message.channel.send("Video already exists in YouTube playlist")
        except Exception as e:
            await message.channel.send("something went wrong. I don't care")
            print(f"{e}")

client.run(config.botToken)

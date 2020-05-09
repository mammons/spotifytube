import os

import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import config
import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from recursiveJson import extract_values

scopes = ["https://www.googleapis.com/auth/youtube"]

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "client_secret_862974823303-5k6td646glkbegi3j4bq83ns87q2a17g.apps.googleusercontent.com.json"

spotify_ccm = SpotifyClientCredentials(
    config.spotify_client_id, config.spotify_secret)
sp = spotipy.Spotify(client_credentials_manager=spotify_ccm)
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


def get_youtube_video_data(spotify_link):
    track_data = sp.track(spotify_link)

    sp_artistname = track_data['artists'][0]['name']
    sp_trackname = track_data['name']

    searchRequest = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=f"{sp_artistname} {sp_trackname}",
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


def add_video_to_playlist(yt_video_id):
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
        # sp.user_playlist_add_tracks("1234656043", "08YWXePJ0DzP9Ls1ccZHT7", message.content)
        await message.channel.send('Looking that shit up on YouTube...')
        try:
            yt_data = get_youtube_video_data(message.content)
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
                        add_video_to_playlist(yt_id)
                        await message.channel.send(f"I went ahead and added that song to the playlist for you: https://www.youtube.com/playlist?list={config.youtube_playlist_id}")
                    except Exception as e:
                        print(f"exception when inserting into playlist: {e}")
                else:
                    await message.channel.send("This is old, man. Keep up.")
        except Exception as e:
            await message.channel.send("something went wrong. i don't care")
            print(f"{e}")

client.run(config.botToken)

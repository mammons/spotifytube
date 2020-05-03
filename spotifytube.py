import os

import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import config
import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

scopes = ["https://www.googleapis.com/auth/youtube"]

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
client_secrets_file = "client_secret_862974823303-5k6td646glkbegi3j4bq83ns87q2a17g.apps.googleusercontent.com.json"

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

spotify_ccm = SpotifyClientCredentials(
    config.spotify_client_id, config.spotify_secret)
sp = spotipy.Spotify(client_credentials_manager=spotify_ccm)
client = discord.Client()


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
            track_data = sp.track(message.content)

            sp_artistname = track_data['artists'][0]['name']
            sp_trackname = track_data['name']


            searchRequest = youtube.search().list(
                part="snippet",
                maxResults=1,
                q=f"{sp_artistname} {sp_trackname}",

            )

            yt_data = searchRequest.execute()
            if not yt_data:
                await message.channel.send("Sorry. I couldn't find anything")
            else:
                yt_id = yt_data['items'][0]['id']['videoId']
                yt_link = f"https://www.youtube.com/watch?v={yt_id}"
                await message.channel.send(f"{yt_link}")

                try:
                    playlistRequest = youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": "PLvkJHpYMGDHsEd0ZW4wuARZ3TtFP5AFPK",
                                "position": 0,
                                "resourceId": {
                                    "kind": "youtube#video",
                                    "videoId": f"{yt_id}"
                                }
                            }
                        }
                    )
                    playListInsertResponse = playlistRequest.execute()
                    await message.channel.send(f"I went ahead and added that song to the playlist for you: https://www.youtube.com/playlist?list=PLvkJHpYMGDHsEd0ZW4wuARZ3TtFP5AFPK")
                except Exception as e:
                    print(f"exception when inserting into playlist: {e}")
        except Exception as e:
            await message.channel.send("something went wrong. i don't care")
            print(f"{e}")

client.run(config.botToken)

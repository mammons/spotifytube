import config
import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
from youtube_api import YouTubeDataAPI

spotify_ccm = SpotifyClientCredentials(
    config.spotify_client_id, config.spotify_secret)
sp = spotipy.Spotify(client_credentials_manager=spotify_ccm)
yt = YouTubeDataAPI(config.youtube_api_key)
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
        await message.channel.send('Looking that shit up on YouTube...')
        try:
            track_data = sp.track(message.content)
            sp_name = track_data['name']
            yt_data = yt.search(sp_name,
                                max_results=1,
                                )
            if not yt_data:
                await message.channel.send("Sorry. I couldn't find anything")
            else:
                yt_id = yt_data[0]['video_id']
                yt_link = f"https://www.youtube.com/watch?v={yt_id}"
                await message.channel.send(f"{yt_link}")
        except:
            await message.channel.send("something went wrong. i don't care")

client.run(config.botToken)

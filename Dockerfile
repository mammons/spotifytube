FROM python:3
RUN pip install -U discord.py
RUN pip install spotipy
RUN pip install youtube-data-api
ADD spotifytube.py /
ADD config.py /
CMD [ "python", "./spotifytube.py" ]
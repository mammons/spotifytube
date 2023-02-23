FROM --platform=linux/amd64 python:3.8-slim-buster
RUN pip3 install --upgrade discord.py
RUN pip3 install spotipy
RUN pip3 install google_auth_oauthlib
RUN pip3 install google-api-python-client
ADD config.py /
ADD recursiveJson.py /
ADD gcp-client-secret.json /
ADD CREDENTIALS_PICKLE_FILE /
ADD .cache-1234656043 /
ADD spotifytube.py /
CMD [ "python3", "./spotifytube.py" ]

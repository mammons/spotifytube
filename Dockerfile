FROM python:3.8
RUN pip install --upgrade discord.py
RUN pip install spotipy
RUN pip install google_auth_oauthlib
RUN pip install google-api-python-client
ADD config.py /
ADD recursiveJson.py /
ADD client_secret_862974823303-5k6td646glkbegi3j4bq83ns87q2a17g.apps.googleusercontent.com.json /
ADD CREDENTIALS_PICKLE_FILE /
ADD .cache-1234656043 /
ADD spotifytube.py /
CMD [ "python", "./spotifytube.py" ]
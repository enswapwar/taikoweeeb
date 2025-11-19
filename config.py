import os

# The full URL base asset URL, with trailing slash.
ASSETS_BASEURL = '/assets/'

# The full URL base song URL, with trailing slash.
SONGS_BASEURL = '/songs/'

# Multiplayer websocket URL. Defaults to /p2 if blank.
MULTIPLAYER_URL = ''

# The email address to display in the "About Simulator" menu.
EMAIL = None

# Whether to use the user account system.
ACCOUNTS = True

# Custom JavaScript file to load with the simulator.
CUSTOM_JS = ''

# Default plugins to load with the simulator.
PLUGINS = [{
    'url': '',
    'start': False,
    'hide': False
}]

# Filetype to use for song previews. (mp3/ogg)
PREVIEW_TYPE = 'mp3'

# ----------------------------------------
# MongoDB (MongoDB Atlas 使用版)
# 旧式の host/database 設定は使えないため削除。
# Render の環境変数 MONGO_URI を必須にする。
# ----------------------------------------
MONGO = {
    'uri': os.getenv('MONGO_URI'),
    'host': None,
    'database': None
}

# Redis server settings (Render では基本無視、必要なら外部RedisをURI指定)
REDIS = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': '127.0.0.1',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_PASSWORD': None,
    'CACHE_REDIS_DB': None
}

# Secret key used for sessions.
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

# Git repository base URL.
URL = 'https://github.com/bui/taiko-web/'

# Google Drive API.
GOOGLE_CREDENTIALS = {
    'gdrive_enabled': False,
    'api_key': '',
    'oauth_client_id': '',
    'project_number': '',
    'min_level': None
}

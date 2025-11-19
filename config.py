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
# MongoDB server settings.
MONGO = {
    'uri': "mongodb+srv://mikan_user_3254:DSTp1LwoBLsWZhVE@cluster0.78nvslg.mongodb.net/?appName=Cluster0",
    'database': 'taikoweeeb'
}


REDIS = {
    'CACHE_TYPE': 'null',
    'CACHE_REDIS_HOST': None,
    'CACHE_REDIS_PORT': None,
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

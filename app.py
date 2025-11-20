#!/usr/bin/env python3

import base64
import bcrypt
import hashlib
try:
    import config
except ModuleNotFoundError:
    raise FileNotFoundError('No such file or directory: \'config.py\'. Copy config.example.py to config.py')
import json
import os
import time
import requests

from functools import wraps
from flask import Flask, g, jsonify, render_template, request, abort, session, send_from_directory
from flask_caching import Cache
from flask_session import Session
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from pymongo import MongoClient
from redis import Redis

# config取得関数
def take_config(name, required=False):
    if hasattr(config, name):
        return getattr(config, name)
    elif required:
        raise ValueError(f'Required option is not defined in config.py: {name}')
    else:
        return None

app = Flask(__name__)

# MongoDB接続
MONGO = take_config('MONGO', required=True)
try:
    client = MongoClient(MONGO.get('uri'))
    db = client[MONGO.get('database')]
except Exception as e:
    print('MongoDB connection error:', e)
    db = None

# Flask セッション
app.secret_key = take_config('SECRET_KEY') or 'change-me'
app.config['SESSION_TYPE'] = 'redis'
redis_config = take_config('REDIS', required=True)
try:
    app.config['SESSION_REDIS'] = Redis(
        host=redis_config.get('CACHE_REDIS_HOST', 'localhost'),
        port=redis_config.get('CACHE_REDIS_PORT', 6379),
        password=redis_config.get('CACHE_REDIS_PASSWORD', None),
        db=redis_config.get('CACHE_REDIS_DB', 0)
    )
except Exception as e:
    print('Redis connection error:', e)
    app.config['SESSION_REDIS'] = None

app.cache = Cache(app, config=redis_config)
sess = Session()
sess.init_app(app)
csrf = CSRFProtect(app)

# DBインデックス作成（DBがない場合はスキップ）
if db:
    try:
        db.users.create_index('username', unique=True)
        db.songs.create_index('id', unique=True)
        db.scores.create_index('username')
    except Exception as e:
        print('Index creation error:', e)

# 独自例外
class HashException(Exception):
    pass

# APIエラー返却
def api_error(message):
    return jsonify({'status': 'error', 'message': message})

# ハッシュ生成
def generate_hash(id, form):
    md5 = hashlib.md5()
    urls = []
    if form.get('type') == 'tja':
        urls = [f"{take_config('SONGS_BASEURL', required=True)}{id}/main.tja"]
    else:
        for diff in ['easy', 'normal', 'hard', 'oni', 'ura']:
            if form.get(f'course_{diff}'):
                urls.append(f"{take_config('SONGS_BASEURL', required=True)}{id}/{diff}.osu")

    for url in urls:
        try:
            if url.startswith("http://") or url.startswith("https://"):
                resp = requests.get(url)
                if resp.status_code != 200:
                    raise HashException(f'Invalid response from {resp.url} (status code {resp.status_code})')
                md5.update(resp.content)
            else:
                path = os.path.normpath(os.path.join("public", url.lstrip("/")))
                if not os.path.isfile(path):
                    raise HashException(f"File not found: {os.path.abspath(path)}")
                with open(path, "rb") as file:
                    md5.update(file.read())
        except Exception as e:
            raise HashException(str(e))

    return base64.b64encode(md5.digest())[:-2].decode('utf-8')

# ログイン必須
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return api_error('not_logged_in')
        return f(*args, **kwargs)
    return wrapper

# 管理者権限チェック
def admin_required(level):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get('username') or not db:
                return abort(403)
            user = db.users.find_one({'username': session.get('username')})
            if not user or user.get('user_level', 0) < level:
                return abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return api_error('invalid_csrf')

@app.before_request
def before_request_func():
    if session.get('session_id') and db:
        if not db.users.find_one({'session_id': session.get('session_id')}):
            session.clear()

@app.route('/')
def route_index():
    version = get_version()
    return render_template('index.html', version=version, config=get_config())

@app.route('/api/csrftoken')
def route_csrftoken():
    return jsonify({'status': 'ok', 'token': generate_csrf()})

@app.route('/src/<path:path>')
def send_src(path):
    return send_from_directory('public/src', path)

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('public/assets', path)

# version.json取得
def get_version():
    version = {'commit': None, 'commit_short': '', 'version': None, 'url': take_config('URL')}
    try:
        if os.path.isfile('version.json'):
            with open('version.json','r') as f:
                ver = json.load(f)
            for k in version.keys():
                if ver.get(k):
                    version[k] = ver.get(k)
    except Exception as e:
        print('Version file error:', e)
    return version

# config取得
def get_config():
    config_out = {
        'songs_baseurl': take_config('SONGS_BASEURL', required=True),
        'assets_baseurl': take_config('ASSETS_BASEURL', required=True)
    }
    return config_out

# サーバ起動
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 34801))
    host = '0.0.0.0'
    app.run(host=host, port=port, debug=True)

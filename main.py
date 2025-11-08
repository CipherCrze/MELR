from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS
import requests
import urllib.parse
import pandas as pd
import numpy as np
from model import RecommendationModel
app = Flask(__name__)
CORS(app)
app.secret_key = 'f7a2c3d1e9b4a6f0c8d5e7b0a3f1c2d4'
ACCESS_TOKEN = "BQA5uwrBX6FSn0aSSY3Dr_qDVKYyWMNyR9jiuPVCqBYZDq_0rmlcWe3CPapYqnKoVxgECL7D253u_0LzZgtgWieYQ5Lehx1imUqOAws7SohDiBKA1-E2drfUP03ERWfvqvA9iB1_bSWSvOMXoi_Waj8K-NsYtiukNXUVx6qid9RXDJpFd8QwoF-4ARGGp5tonomCuTqQPDBHfRDrS3Vi7xMn8ueR3jGs-nahS_B2sR8HgSot7rG3pLAV23U38PS8tTM"
CLIENT_ID = '544167d5c05d41f3a022b38f0ed403c0'
CLIENT_SECRET = 'ec5e94361c284bb1acaa18a4a2785208'
REDIRECT_URI = 'http://localhost:5000/callback'
SCOPE = 'user-read-private user-read-email user-top-read'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'


# engine = RecommendationModel()  # Adjust based on your features

@app.route('/')
def index():
    return 'Welcome to the Spotify OAuth Demo. <a href="/login">Log in with Spotify</a>'

@app.route('/login')
def login():
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if code:
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }
        response = requests.post(TOKEN_URL, data=token_data)
        if response.status_code == 200:
            token_info = response.json()
            session['access_token'] = token_info['access_token']
            # return jsonify(session['access_token'])
            session['refresh_token'] = token_info['refresh_token']
            session['expires_at'] = token_info['expires_in']
            return redirect('http://localhost:3000/auth/create-profile')
        else:
            return jsonify({"error": "Failed to obtain access token"}), 400
    else:
        return jsonify({"error": "Authorization code not found"}), 400

@app.route('/profile')
def profile():
    access_token = ACCESS_TOKEN
    if not access_token:
        return redirect('/login')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(API_BASE_URL + 'me', headers=headers)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch user profile"}), response.status_code

@app.route('/profile-data')
def profileData():
    access_token = ACCESS_TOKEN
    if not access_token:
        return redirect('/login')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(API_BASE_URL + 'me', headers=headers)
    if response.status_code == 200:
        return jsonify({"img":response.json()["images"][0]["url"], "username": response.json()["display_name"]})
    else:
        return jsonify({"error": "Failed to fetch user profile"}), response.status_code

@app.route('/recommendations')
def recommendations():
    user_top_df = pd.read_csv('./user_top5.csv')
    all_songs_df = pd.read_csv('./spotify_data.csv')
    engine = RecommendationModel(user_top_tracks_df=user_top_df)
    recommendations = engine.generate_personalized_recos(all_songs_df, n_neighbors=10, diversify=True)
    if not recommendations.empty:
        return jsonify({"track_ids": [trackID for trackID in recommendations['track_id']], "access_token": ACCESS_TOKEN})

def getTrackViaID(trackID):
    access_token = ACCESS_TOKEN
    if not access_token:
        return redirect('/login')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(API_BASE_URL + f"tracks/{trackID}", headers=headers)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to get recommendations"}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
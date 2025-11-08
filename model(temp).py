import pandas as pd
import numpy as np
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

class RecommendationModel:
    def _init_(self, client_id, client_secret, redirect_uri, scope):
        self.scope = scope
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope
        ))

        self.feature_columns = ['danceability', 'acousticness', 'liveness', 'energy', 'valence', 'tempo']
        self.user_feedback = {
            'liked': set(),
            'disliked': set()
        }

        self.user_top_tracks_df = self.get_user_top_tracks()
        self.personal_vector = self.get_personal_vector_from_listening_history()

    def get_user_top_tracks(self, limit=50, time_range='medium_term'):
        top_tracks = self.sp.current_user_top_tracks(limit=limit, time_range=time_range)
        track_data = []
        for track in top_tracks['items']:
            features = self.sp.audio_features(track['id'])[0]
            if features:
                track_data.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'danceability': features['danceability'],
                    'acousticness': features['acousticness'],
                    'liveness': features['liveness'],
                    'energy': features['energy'],
                    'valence': features['valence'],
                    'tempo': features['tempo'],
                    'popularity': track['popularity'],
                    'genre': ' '.join(self.get_artist_genres(track['artists'][0]['id'])),
                })
        return pd.DataFrame(track_data)

    def get_artist_genres(self, artist_id):
        try:
            artist = self.sp.artist(artist_id)
            return artist.get('genres', [])
        except:
            return []

    def get_personal_vector_from_listening_history(self):
        df = self.user_top_tracks_df.copy()
        if df.empty:
            return np.zeros(len(self.feature_columns))
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(df[self.feature_columns])
        return np.mean(scaled_features, axis=0)

    def update_feedback(self, track_id, liked=True):
        if liked:
            self.user_feedback['liked'].add(track_id)
            self.user_feedback['disliked'].discard(track_id)
        else:
            self.user_feedback['disliked'].add(track_id)
            self.user_feedback['liked'].discard(track_id)

    def aggregate_feedback_vector(self, track_ids):
        vectors = []
        for tid in track_ids:
            try:
                features = self.sp.audio_features(tid)[0]
                if features:
                    vectors.append([
                        features['danceability'],
                        features['acousticness'],
                        features['liveness'],
                        features['energy'],
                        features['valence'],
                        features['tempo']
                    ])
            except:
                continue
        if not vectors:
            return np.zeros(len(self.feature_columns))
        return np.mean(vectors, axis=0)

    def generate_personalized_recos(self, df):
        liked_vector = self.aggregate_feedback_vector(self.user_feedback['liked'])
        disliked_vector = self.aggregate_feedback_vector(self.user_feedback['disliked'])

        # Combine listening history and feedback
        combined_vector = self.personal_vector + 0.75 * liked_vector - 0.5 * disliked_vector

        # Normalize dataset features
        scaler = MinMaxScaler()
        df_scaled = df.copy()
        df_scaled[self.feature_columns] = scaler.fit_transform(df_scaled[self.feature_columns])

        # Calculate cosine similarity
        sim_scores = cosine_similarity(df_scaled[self.feature_columns], combined_vector.reshape(1, -1))
        df_scaled['sim'] = sim_scores[:, 0]
        return df_scaled.sort_values('sim', ascending=False).head(10)
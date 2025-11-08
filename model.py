import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.impute import SimpleImputer
from fuzzywuzzy import fuzz

class RecommendationModel:
    def __init__(self, user_top_tracks_df):
        self.feature_columns = ['danceability', 'acousticness', 'liveness', 'energy', 'valence', 'tempo']
        self.user_top_tracks_df = user_top_tracks_df
        self.user_feedback = {
            'liked': set(user_top_tracks_df['id'].values),
            'disliked': set()
        }
        self.personal_vector = self.get_personal_vector_from_listening_history()

    def get_personal_vector_from_listening_history(self):
        df = self.user_top_tracks_df.copy()
        if df.empty:
            return np.zeros(len(self.feature_columns))
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(df[self.feature_columns])
        return np.mean(scaled_features, axis=0)

    def aggregate_feedback_vector(self, track_ids, source_df):
        vectors = []
        for tid in track_ids:
            row = source_df[source_df['id'] == tid]
            if not row.empty:
                vectors.append(row[self.feature_columns].values[0])
        if not vectors:
            return np.zeros(len(self.feature_columns))
        return np.mean(vectors, axis=0)

    def is_similar_artist(self, artist_name, user_artists, threshold=70):
        return any(fuzz.token_set_ratio(artist_name.lower(), artist.lower()) >= threshold for artist in user_artists)

    def generate_personalized_recos(self, all_tracks_df, n_neighbors=10, year_tolerance=3, diversify=True):
        # 1. Extract filter info from user top tracks
        user_genres = set(self.user_top_tracks_df['genre'].dropna().unique())
        user_artists = set(self.user_top_tracks_df['artist'].dropna().unique())
        avg_year = self.user_top_tracks_df['year'].dropna().mean()
        min_year = avg_year - year_tolerance
        max_year = avg_year + year_tolerance

        # 2. Filter by genre, year and popularity
        filtered_df = all_tracks_df[
            (all_tracks_df['genre'].isin(user_genres)) &
            (all_tracks_df['year'] >= min_year) &
            (all_tracks_df['year'] <= max_year) &
            (all_tracks_df['popularity'] >= 50)
        ].copy()

        # 3. Optional artist filter
        if not diversify:
            filtered_df = filtered_df[
                filtered_df['artist'].apply(lambda a: self.is_similar_artist(a, user_artists))
            ]

        if filtered_df.empty:
            print("⚠ No songs found with matching genre, year, artist (if diversify=False), and popularity filters.")
            return pd.DataFrame()

        # 4. Vector construction
        liked_vector = self.aggregate_feedback_vector(self.user_feedback['liked'], all_tracks_df)
        disliked_vector = self.aggregate_feedback_vector(self.user_feedback['disliked'], all_tracks_df)
        combined_vector = self.personal_vector + 0.75 * liked_vector - 0.5 * disliked_vector

        # 5. Normalize and impute
        scaler = MinMaxScaler()
        imputer = SimpleImputer(strategy='mean')
        filtered_df[self.feature_columns] = scaler.fit_transform(filtered_df[self.feature_columns])
        filtered_df[self.feature_columns] = imputer.fit_transform(filtered_df[self.feature_columns])

        # 6. Nearest Neighbors
        knn = NearestNeighbors(n_neighbors=min(n_neighbors, len(filtered_df)), metric='euclidean')
        knn.fit(filtered_df[self.feature_columns])
        distances, indices = knn.kneighbors([combined_vector])

        recommended_df = filtered_df.iloc[indices[0]].copy()
        recommended_df['distance'] = distances[0]
        return recommended_df.sort_values('distance')

def recommend():
    user_top_df = pd.read_csv('./user_top5.csv')
    all_songs_df = pd.read_csv('./spotify_data.csv')
    # Create recommendation engine
    engine = RecommendationModel(user_top_tracks_df=user_top_df)
    # Run with diversify=True by default
    recommendations = engine.generate_personalized_recos(all_songs_df, n_neighbors=10, diversify=True)
    if not recommendations.empty:
        # print("🎵 Top Recommended Songs:")
        return recommendations[['name', 'artist', 'genre', 'year', 'popularity', 'track_id', 'distance']]
    return []
    # else:
        # print("❌ No recommendations available based on the filters.")
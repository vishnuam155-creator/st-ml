"""
Machine Learning Predictor Module
Uses ML to predict stock movements and rank candidates
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os

from .data_fetcher import DataFetcher
from .technical_indicators import TechnicalIndicators


class MLPredictor:
    """
    Machine Learning predictor for stock movement
    Predicts if stock will move up/down and ranks candidates
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or 'models/stock_predictor.pkl'
        self.scaler_path = 'models/scaler.pkl'

        self.model = None
        self.scaler = None
        self.data_fetcher = DataFetcher()
        self.tech_indicators = TechnicalIndicators()

        # Load model if exists
        self._load_model()

    def _load_model(self):
        """Load saved model and scaler"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print(f"Loaded ML model from {self.model_path}")
            except Exception as e:
                print(f"Error loading model: {e}")
                self.model = None
                self.scaler = None

    def _save_model(self):
        """Save model and scaler"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)

            print(f"Model saved to {self.model_path}")
        except Exception as e:
            print(f"Error saving model: {e}")

    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for ML model

        Features:
        - Technical indicators (EMA, RSI, ATR, VWAP)
        - Price momentum
        - Volume patterns
        - Trend indicators

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with features
        """
        if len(data) < 50:
            return pd.DataFrame()

        # Add all technical indicators
        data = self.tech_indicators.add_all_indicators(data)

        features = pd.DataFrame()

        # Price features
        features['price_change_1'] = data['Close'].pct_change(1)
        features['price_change_3'] = data['Close'].pct_change(3)
        features['price_change_5'] = data['Close'].pct_change(5)

        # Distance from EMAs
        features['dist_from_ema20'] = (data['Close'] - data['EMA_20']) / data['Close']
        features['dist_from_ema200'] = (data['Close'] - data['EMA_200']) / data['Close']
        features['dist_from_vwap'] = (data['Close'] - data['VWAP']) / data['Close']

        # EMA relationships
        features['ema20_above_ema200'] = (data['EMA_20'] > data['EMA_200']).astype(int)
        features['price_above_vwap'] = (data['Close'] > data['VWAP']).astype(int)

        # RSI
        features['rsi'] = data['RSI']
        features['rsi_overbought'] = (data['RSI'] > 70).astype(int)
        features['rsi_oversold'] = (data['RSI'] < 30).astype(int)

        # ATR normalized
        features['atr_pct'] = data['ATR'] / data['Close']

        # Volume features
        features['volume_ratio'] = data['Volume_Ratio']
        features['volume_surge'] = (data['Volume_Ratio'] > 1.5).astype(int)

        # Volatility
        features['price_range'] = (data['High'] - data['Low']) / data['Close']

        # Trend strength
        features['trend_strength'] = features['dist_from_ema200'].abs()

        # Higher highs / Lower lows
        features['hh'] = (data['High'] > data['High'].shift(1)).astype(int)
        features['ll'] = (data['Low'] < data['Low'].shift(1)).astype(int)

        # Fill NaN values
        features = features.fillna(0)

        return features

    def create_labels(self, data: pd.DataFrame, forward_periods: int = 5) -> pd.Series:
        """
        Create labels for training
        1 if price goes up in next N periods, 0 if goes down

        Args:
            data: DataFrame with OHLCV data
            forward_periods: Number of periods to look ahead

        Returns:
            Series with labels (1 for up, 0 for down)
        """
        future_return = data['Close'].shift(-forward_periods) / data['Close'] - 1

        # Label as 1 if future return > 0.5%, 0 if < -0.5%, else neutral (drop)
        labels = pd.Series(index=data.index, dtype=int)
        labels[future_return > 0.005] = 1  # Up
        labels[future_return < -0.005] = 0  # Down
        labels[(future_return >= -0.005) & (future_return <= 0.005)] = -1  # Neutral (will drop)

        return labels

    def train_model(self, symbols: List[str], period: str = '3mo'):
        """
        Train ML model on historical data

        Args:
            symbols: List of stock symbols to train on
            period: Historical period for training data
        """
        print("\n" + "="*60)
        print("🤖 TRAINING ML MODEL")
        print("="*60)

        all_features = []
        all_labels = []

        print(f"\nCollecting training data from {len(symbols)} stocks...")

        for symbol in symbols:
            try:
                # Get historical data
                data = self.data_fetcher.get_historical_data(symbol, period=period, interval='1d')

                if data.empty or len(data) < 50:
                    continue

                # Extract features
                features = self.extract_features(data)

                if features.empty:
                    continue

                # Create labels
                labels = self.create_labels(data, forward_periods=5)

                # Remove neutral labels
                valid_idx = labels != -1
                features = features[valid_idx]
                labels = labels[valid_idx]

                all_features.append(features)
                all_labels.append(labels)

                print(f"  ✓ {symbol}: {len(features)} samples")

            except Exception as e:
                print(f"  ✗ {symbol}: Error - {e}")
                continue

        if not all_features:
            print("⚠️  No training data collected!")
            return

        # Combine all data
        X = pd.concat(all_features, axis=0)
        y = pd.concat(all_labels, axis=0)

        # Remove any remaining NaN
        valid_idx = ~(X.isna().any(axis=1) | y.isna())
        X = X[valid_idx]
        y = y[valid_idx]

        print(f"\nTotal training samples: {len(X)}")
        print(f"  Up: {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
        print(f"  Down: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        print("\nTraining Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_scaled, y)

        # Calculate accuracy
        train_accuracy = self.model.score(X_scaled, y)
        print(f"Training accuracy: {train_accuracy:.2%}")

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("\nTop 10 most important features:")
        for i, row in feature_importance.head(10).iterrows():
            print(f"  {row['feature']:25s}: {row['importance']:.4f}")

        # Save model
        self._save_model()

        print("\n✓ Model training complete!")

    def predict_movement(self, symbol: str) -> Dict:
        """
        Predict stock movement

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with prediction and probability
        """
        if self.model is None or self.scaler is None:
            return {
                'prediction': None,
                'probability': 0,
                'confidence': 0,
                'error': 'Model not trained'
            }

        try:
            # Get recent data
            data = self.data_fetcher.get_intraday_data(symbol, interval='5m')

            if data.empty or len(data) < 50:
                return {
                    'prediction': None,
                    'probability': 0,
                    'confidence': 0,
                    'error': 'Insufficient data'
                }

            # Extract features for latest candle
            features = self.extract_features(data)

            if features.empty:
                return {
                    'prediction': None,
                    'probability': 0,
                    'confidence': 0,
                    'error': 'Feature extraction failed'
                }

            # Get latest features
            X = features.iloc[-1:].values

            # Scale features
            X_scaled = self.scaler.transform(X)

            # Predict
            prediction = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]

            # Calculate confidence (how far from 50-50)
            confidence = max(probabilities) - 0.5

            return {
                'prediction': 'up' if prediction == 1 else 'down',
                'probability': probabilities[1],  # Probability of up move
                'confidence': confidence * 2,  # Scale to 0-1
                'probabilities': {
                    'up': probabilities[1],
                    'down': probabilities[0],
                }
            }

        except Exception as e:
            return {
                'prediction': None,
                'probability': 0,
                'confidence': 0,
                'error': str(e)
            }

    def rank_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        Rank candidates using ML predictions

        Args:
            candidates: List of candidate stocks

        Returns:
            Ranked list of candidates with ML scores
        """
        print("\n" + "="*60)
        print("🤖 ML RANKING OF CANDIDATES")
        print("="*60)

        if self.model is None:
            print("⚠️  Model not trained. Skipping ML ranking.")
            return candidates

        ranked_candidates = []

        for candidate in candidates:
            symbol = candidate['symbol']

            # Get prediction
            prediction = self.predict_movement(symbol)

            # Add prediction to candidate
            candidate['ml_prediction'] = prediction['prediction']
            candidate['ml_probability'] = prediction['probability']
            candidate['ml_confidence'] = prediction['confidence']

            # Calculate combined score (ML + technical)
            # Combine ML prediction with technical setup quality if available
            ml_score = prediction['probability'] if prediction['prediction'] == 'up' else (1 - prediction['probability'])
            ml_score *= prediction['confidence']  # Weight by confidence

            candidate['ml_score'] = ml_score * 100  # Scale to 0-100

            ranked_candidates.append(candidate)

            print(f"  {symbol:15s} | Prediction: {prediction['prediction']:5s} | "
                  f"Prob: {prediction['probability']:.2%} | "
                  f"Confidence: {prediction['confidence']:.2%} | "
                  f"Score: {candidate['ml_score']:.0f}/100")

        # Sort by ML score
        ranked_candidates.sort(key=lambda x: x.get('ml_score', 0), reverse=True)

        return ranked_candidates

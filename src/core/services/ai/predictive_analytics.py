"""
Advanced AI Features for FS Reconciliation Agents.

This module provides:
- Predictive analytics for break detection
- Anomaly detection
- Intelligent recommendations
- Self-improving models
- Pattern recognition
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.cluster import DBSCAN
import joblib
import json

from src.core.services.caching.redis_cache import get_cache_service
from src.core.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class PredictiveAnalytics:
    """Predictive analytics service for reconciliation breaks."""
    
    def __init__(self):
        self.break_predictor = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.model_version = "1.0.0"
        self.last_training = None
        self.accuracy_threshold = 0.85
        
    async def initialize(self):
        """Initialize the predictive analytics service."""
        try:
            # Load existing models if available
            await self.load_models()
            logger.info("Predictive analytics service initialized")
        except Exception as e:
            logger.warning(f"Could not load existing models: {e}")
            # Initialize with default models
            self.break_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    async def load_models(self):
        """Load trained models from cache or file."""
        cache_service = get_cache_service()
        
        # Try to load from cache first
        break_predictor_data = await cache_service.get("ai:model:break_predictor")
        anomaly_detector_data = await cache_service.get("ai:model:anomaly_detector")
        
        if break_predictor_data and anomaly_detector_data:
            self.break_predictor = joblib.loads(break_predictor_data)
            self.anomaly_detector = joblib.loads(anomaly_detector_data)
            logger.info("Models loaded from cache")
        else:
            # Try to load from file
            try:
                self.break_predictor = joblib.load('models/break_predictor.pkl')
                self.anomaly_detector = joblib.load('models/anomaly_detector.pkl')
                logger.info("Models loaded from file")
            except FileNotFoundError:
                raise Exception("No trained models found")
    
    async def save_models(self):
        """Save trained models to cache and file."""
        cache_service = get_cache_service()
        
        # Save to cache
        break_predictor_data = joblib.dumps(self.break_predictor)
        anomaly_detector_data = joblib.dumps(self.anomaly_detector)
        
        await cache_service.set("ai:model:break_predictor", break_predictor_data, ttl=86400)  # 24 hours
        await cache_service.set("ai:model:anomaly_detector", anomaly_detector_data, ttl=86400)
        
        # Save to file
        joblib.dump(self.break_predictor, 'models/break_predictor.pkl')
        joblib.dump(self.anomaly_detector, 'models/anomaly_detector.pkl')
        
        logger.info("Models saved successfully")
    
    def extract_features(self, transaction_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Extract features from transaction data for prediction."""
        features = []
        
        for transaction in transaction_data:
            feature_vector = {
                'amount': float(transaction.get('amount', 0)),
                'quantity': float(transaction.get('quantity', 0)),
                'fx_rate': float(transaction.get('fx_rate', 1.0)),
                'market_price': float(transaction.get('market_price', 0)),
                'confidence_score': float(transaction.get('confidence_score', 0.5)),
                'day_of_week': transaction.get('trade_date', datetime.now()).weekday(),
                'month': transaction.get('trade_date', datetime.now()).month,
                'hour': transaction.get('trade_date', datetime.now()).hour,
                'is_weekend': 1 if transaction.get('trade_date', datetime.now()).weekday() >= 5 else 0,
                'amount_log': np.log1p(float(transaction.get('amount', 0))),
                'quantity_log': np.log1p(float(transaction.get('quantity', 0))),
                'price_volatility': self._calculate_price_volatility(transaction),
                'amount_anomaly_score': self._calculate_amount_anomaly(transaction),
                'time_anomaly_score': self._calculate_time_anomaly(transaction)
            }
            features.append(feature_vector)
        
        return pd.DataFrame(features)
    
    def _calculate_price_volatility(self, transaction: Dict[str, Any]) -> float:
        """Calculate price volatility for a transaction."""
        try:
            market_price = float(transaction.get('market_price', 0))
            if market_price > 0:
                # Simple volatility calculation based on price deviation
                return abs(market_price - 100) / 100  # Assuming 100 as baseline
            return 0.0
        except:
            return 0.0
    
    def _calculate_amount_anomaly(self, transaction: Dict[str, Any]) -> float:
        """Calculate amount anomaly score."""
        try:
            amount = float(transaction.get('amount', 0))
            # Simple anomaly detection based on amount thresholds
            if amount > 1000000:  # High value transactions
                return 0.8
            elif amount < 1000:  # Low value transactions
                return 0.6
            else:
                return 0.2
        except:
            return 0.5
    
    def _calculate_time_anomaly(self, transaction: Dict[str, Any]) -> float:
        """Calculate time-based anomaly score."""
        try:
            trade_date = transaction.get('trade_date', datetime.now())
            hour = trade_date.hour
            
            # Anomaly score based on trading hours
            if 9 <= hour <= 16:  # Normal trading hours
                return 0.2
            elif 6 <= hour <= 8 or 17 <= hour <= 19:  # Extended hours
                return 0.5
            else:  # After hours
                return 0.8
        except:
            return 0.5
    
    async def predict_break_probability(self, transaction_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict the probability of breaks for transactions."""
        if not self.break_predictor:
            logger.warning("Break predictor model not available")
            return []
        
        try:
            # Extract features
            features_df = self.extract_features(transaction_data)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_df)
            
            # Make predictions
            break_probabilities = self.break_predictor.predict_proba(features_scaled)
            
            # Prepare results
            results = []
            for i, transaction in enumerate(transaction_data):
                result = {
                    'transaction_id': transaction.get('id'),
                    'break_probability': float(break_probabilities[i][1]),  # Probability of break
                    'confidence': float(break_probabilities[i].max()),
                    'risk_level': self._classify_risk_level(break_probabilities[i][1]),
                    'recommended_actions': self._get_recommended_actions(break_probabilities[i][1]),
                    'features_used': features_df.columns.tolist()
                }
                results.append(result)
            
            # Log predictions
            await audit_logger.log_ai_prediction(
                session_id=f"prediction_{datetime.now().isoformat()}",
                model_version=self.model_version,
                predictions_count=len(results),
                avg_confidence=np.mean([r['confidence'] for r in results])
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in break prediction: {e}")
            return []
    
    def _classify_risk_level(self, probability: float) -> str:
        """Classify risk level based on break probability."""
        if probability >= 0.8:
            return "high"
        elif probability >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _get_recommended_actions(self, probability: float) -> List[str]:
        """Get recommended actions based on break probability."""
        actions = []
        
        if probability >= 0.8:
            actions.extend([
                "Immediate manual review required",
                "Escalate to senior analyst",
                "Check for data quality issues",
                "Verify with external sources"
            ])
        elif probability >= 0.5:
            actions.extend([
                "Schedule for review",
                "Monitor closely",
                "Check historical patterns"
            ])
        else:
            actions.append("Standard processing")
        
        return actions
    
    async def detect_anomalies(self, transaction_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in transaction data."""
        if not self.anomaly_detector:
            logger.warning("Anomaly detector model not available")
            return []
        
        try:
            # Extract features
            features_df = self.extract_features(transaction_data)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_df)
            
            # Detect anomalies
            anomaly_scores = self.anomaly_detector.decision_function(features_scaled)
            anomaly_predictions = self.anomaly_detector.predict(features_scaled)
            
            # Prepare results
            results = []
            for i, transaction in enumerate(transaction_data):
                is_anomaly = anomaly_predictions[i] == -1
                result = {
                    'transaction_id': transaction.get('id'),
                    'is_anomaly': bool(is_anomaly),
                    'anomaly_score': float(anomaly_scores[i]),
                    'anomaly_type': self._classify_anomaly_type(transaction, anomaly_scores[i]),
                    'severity': self._classify_anomaly_severity(anomaly_scores[i]),
                    'explanation': self._explain_anomaly(transaction, anomaly_scores[i])
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return []
    
    def _classify_anomaly_type(self, transaction: Dict[str, Any], score: float) -> str:
        """Classify the type of anomaly."""
        amount = float(transaction.get('amount', 0))
        
        if amount > 1000000:
            return "high_value_transaction"
        elif amount < 1000:
            return "low_value_transaction"
        elif score < -0.5:
            return "pattern_deviation"
        else:
            return "moderate_deviation"
    
    def _classify_anomaly_severity(self, score: float) -> str:
        """Classify anomaly severity."""
        if score < -0.8:
            return "critical"
        elif score < -0.5:
            return "high"
        elif score < -0.2:
            return "medium"
        else:
            return "low"
    
    def _explain_anomaly(self, transaction: Dict[str, Any], score: float) -> str:
        """Provide explanation for detected anomaly."""
        explanations = []
        
        amount = float(transaction.get('amount', 0))
        if amount > 1000000:
            explanations.append("Unusually high transaction amount")
        elif amount < 1000:
            explanations.append("Unusually low transaction amount")
        
        if score < -0.5:
            explanations.append("Significant deviation from normal patterns")
        
        if not explanations:
            explanations.append("Minor deviation from expected behavior")
        
        return "; ".join(explanations)
    
    async def train_models(self, training_data: List[Dict[str, Any]], labels: List[int]):
        """Train the predictive models with new data."""
        try:
            # Extract features
            features_df = self.extract_features(training_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features_df, labels, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train break predictor
            self.break_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
            self.break_predictor.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.break_predictor.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Train anomaly detector
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
            self.anomaly_detector.fit(X_train_scaled)
            
            # Save models if accuracy is good
            if accuracy >= self.accuracy_threshold:
                await self.save_models()
                self.last_training = datetime.now()
                
                logger.info(f"Models trained successfully. Accuracy: {accuracy:.3f}")
                
                # Log training results
                await audit_logger.log_model_training(
                    session_id=f"training_{datetime.now().isoformat()}",
                    model_version=self.model_version,
                    accuracy=accuracy,
                    training_samples=len(X_train),
                    test_samples=len(X_test)
                )
                
                return {
                    'success': True,
                    'accuracy': accuracy,
                    'training_samples': len(X_train),
                    'test_samples': len(X_test)
                }
            else:
                logger.warning(f"Model accuracy {accuracy:.3f} below threshold {self.accuracy_threshold}")
                return {
                    'success': False,
                    'accuracy': accuracy,
                    'reason': 'Accuracy below threshold'
                }
                
        except Exception as e:
            logger.error(f"Error in model training: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_model_performance(self) -> Dict[str, Any]:
        """Get current model performance metrics."""
        return {
            'model_version': self.model_version,
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'accuracy_threshold': self.accuracy_threshold,
            'models_loaded': bool(self.break_predictor and self.anomaly_detector),
            'features_count': 15,  # Number of features used
            'supported_models': ['break_predictor', 'anomaly_detector']
        }
    
    async def get_intelligent_recommendations(self, transaction_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get intelligent recommendations for transaction processing."""
        recommendations = []
        
        # Get predictions and anomalies
        predictions = await self.predict_break_probability(transaction_data)
        anomalies = await self.detect_anomalies(transaction_data)
        
        for i, transaction in enumerate(transaction_data):
            pred = predictions[i] if i < len(predictions) else {}
            anomaly = anomalies[i] if i < len(anomalies) else {}
            
            recommendation = {
                'transaction_id': transaction.get('id'),
                'priority': self._calculate_priority(pred, anomaly),
                'processing_strategy': self._get_processing_strategy(pred, anomaly),
                'review_required': self._should_review(pred, anomaly),
                'estimated_processing_time': self._estimate_processing_time(pred, anomaly),
                'risk_factors': self._identify_risk_factors(transaction, pred, anomaly),
                'optimization_suggestions': self._get_optimization_suggestions(transaction, pred, anomaly)
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_priority(self, pred: Dict[str, Any], anomaly: Dict[str, Any]) -> str:
        """Calculate processing priority."""
        break_prob = pred.get('break_probability', 0)
        is_anomaly = anomaly.get('is_anomaly', False)
        
        if break_prob >= 0.8 or is_anomaly:
            return "high"
        elif break_prob >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _get_processing_strategy(self, pred: Dict[str, Any], anomaly: Dict[str, Any]) -> str:
        """Get recommended processing strategy."""
        break_prob = pred.get('break_probability', 0)
        is_anomaly = anomaly.get('is_anomaly', False)
        
        if break_prob >= 0.8 or is_anomaly:
            return "manual_review"
        elif break_prob >= 0.5:
            return "supervised_automation"
        else:
            return "automated_processing"
    
    def _should_review(self, pred: Dict[str, Any], anomaly: Dict[str, Any]) -> bool:
        """Determine if manual review is required."""
        break_prob = pred.get('break_probability', 0)
        is_anomaly = anomaly.get('is_anomaly', False)
        
        return break_prob >= 0.7 or is_anomaly
    
    def _estimate_processing_time(self, pred: Dict[str, Any], anomaly: Dict[str, Any]) -> int:
        """Estimate processing time in minutes."""
        break_prob = pred.get('break_probability', 0)
        is_anomaly = anomaly.get('is_anomaly', False)
        
        if break_prob >= 0.8 or is_anomaly:
            return 30  # 30 minutes for high-risk items
        elif break_prob >= 0.5:
            return 15  # 15 minutes for medium-risk items
        else:
            return 2   # 2 minutes for low-risk items
    
    def _identify_risk_factors(self, transaction: Dict[str, Any], pred: Dict[str, Any], anomaly: Dict[str, Any]) -> List[str]:
        """Identify risk factors for a transaction."""
        risk_factors = []
        
        amount = float(transaction.get('amount', 0))
        if amount > 1000000:
            risk_factors.append("High value transaction")
        elif amount < 1000:
            risk_factors.append("Low value transaction")
        
        if pred.get('break_probability', 0) >= 0.7:
            risk_factors.append("High break probability")
        
        if anomaly.get('is_anomaly', False):
            risk_factors.append("Anomalous pattern detected")
        
        return risk_factors
    
    def _get_optimization_suggestions(self, transaction: Dict[str, Any], pred: Dict[str, Any], anomaly: Dict[str, Any]) -> List[str]:
        """Get optimization suggestions."""
        suggestions = []
        
        if pred.get('break_probability', 0) >= 0.8:
            suggestions.append("Consider pre-validation checks")
            suggestions.append("Implement additional data quality controls")
        
        if anomaly.get('is_anomaly', False):
            suggestions.append("Review data source reliability")
            suggestions.append("Update validation rules")
        
        return suggestions


# Global instance
_predictive_analytics: Optional[PredictiveAnalytics] = None


async def get_predictive_analytics() -> PredictiveAnalytics:
    """Get global predictive analytics instance."""
    global _predictive_analytics
    if not _predictive_analytics:
        _predictive_analytics = PredictiveAnalytics()
        await _predictive_analytics.initialize()
    return _predictive_analytics

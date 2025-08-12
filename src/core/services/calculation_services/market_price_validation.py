"""
Market Price Validation Service for FS Reconciliation Agents.

This module implements market price validation, tolerance rules,
and anomaly detection for financial instruments.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Union, Optional, Dict, Any, List, Tuple
from decimal import Decimal
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class PriceToleranceType(str, Enum):
    """Price tolerance types."""
    
    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"
    BID_ASK_SPREAD = "bid_ask_spread"
    VOLATILITY_BASED = "volatility_based"


class SecurityType(str, Enum):
    """Security types for price validation."""
    
    EQUITY = "equity"
    BOND = "bond"
    MONEY_MARKET = "money_market"
    FX = "fx"
    COMMODITY = "commodity"
    DERIVATIVE = "derivative"


class MarketPriceValidator:
    """Validator for market prices and price anomalies."""
    
    def __init__(self):
        """Initialize the market price validator."""
        self.price_history = {}
        self.tolerance_rules = {
            SecurityType.EQUITY: {"percentage": 0.05, "absolute": 0.01},  # 5% or $0.01
            SecurityType.BOND: {"percentage": 0.02, "absolute": 0.001},   # 2% or 0.1%
            SecurityType.MONEY_MARKET: {"percentage": 0.01, "absolute": 0.0001},  # 1% or 0.01%
            SecurityType.FX: {"percentage": 0.001, "absolute": 0.0001},   # 0.1% or 0.01%
            SecurityType.COMMODITY: {"percentage": 0.03, "absolute": 0.01},  # 3% or $0.01
            SecurityType.DERIVATIVE: {"percentage": 0.10, "absolute": 0.01}  # 10% or $0.01
        }
        
        self.bid_ask_spread_thresholds = {
            SecurityType.EQUITY: 0.02,      # 2% spread
            SecurityType.BOND: 0.01,        # 1% spread
            SecurityType.MONEY_MARKET: 0.005,  # 0.5% spread
            SecurityType.FX: 0.001,         # 0.1% spread
            SecurityType.COMMODITY: 0.01,   # 1% spread
            SecurityType.DERIVATIVE: 0.05   # 5% spread
        }
    
    def validate_price(self, security_id: str, price: float, reference_price: float,
                      security_type: SecurityType = SecurityType.EQUITY,
                      tolerance_type: PriceToleranceType = PriceToleranceType.PERCENTAGE) -> Dict[str, Any]:
        """
        Validate a market price against reference price.
        
        Args:
            security_id: Security identifier
            price: Current market price
            reference_price: Reference price for comparison
            security_type: Type of security
            tolerance_type: Type of tolerance to apply
            
        Returns:
            Price validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "price_difference": 0.0,
            "price_difference_pct": 0.0,
            "tolerance_exceeded": False,
            "confidence_score": 1.0
        }
        
        # Basic validation
        if price <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Price must be positive")
            return validation_result
        
        if reference_price <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Reference price must be positive")
            return validation_result
        
        # Calculate price difference
        price_diff = abs(price - reference_price)
        price_diff_pct = price_diff / reference_price
        
        validation_result["price_difference"] = price_diff
        validation_result["price_difference_pct"] = price_diff_pct
        
        # Apply tolerance rules
        tolerance_rules = self.tolerance_rules.get(security_type, {"percentage": 0.05, "absolute": 0.01})
        
        if tolerance_type == PriceToleranceType.PERCENTAGE:
            tolerance = tolerance_rules["percentage"]
            tolerance_exceeded = price_diff_pct > tolerance
        elif tolerance_type == PriceToleranceType.ABSOLUTE:
            tolerance = tolerance_rules["absolute"]
            tolerance_exceeded = price_diff > tolerance
        else:
            tolerance_exceeded = False
        
        validation_result["tolerance_exceeded"] = tolerance_exceeded
        
        if tolerance_exceeded:
            validation_result["warnings"].append(f"Price difference {price_diff_pct:.2%} exceeds tolerance {tolerance:.2%}")
            validation_result["confidence_score"] = max(0.3, 1.0 - price_diff_pct)
        
        # Check for extreme price movements
        if price_diff_pct > 0.5:  # 50% difference
            validation_result["warnings"].append("Extreme price movement detected")
            validation_result["confidence_score"] = 0.1
        
        return validation_result
    
    def validate_bid_ask_spread(self, bid_price: float, ask_price: float,
                               security_type: SecurityType = SecurityType.EQUITY) -> Dict[str, Any]:
        """
        Validate bid-ask spread.
        
        Args:
            bid_price: Bid price
            ask_price: Ask price
            security_type: Type of security
            
        Returns:
            Bid-ask spread validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "spread": 0.0,
            "spread_pct": 0.0,
            "spread_exceeds_threshold": False
        }
        
        # Basic validation
        if bid_price <= 0 or ask_price <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Bid and ask prices must be positive")
            return validation_result
        
        if bid_price >= ask_price:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Bid price must be less than ask price")
            return validation_result
        
        # Calculate spread
        spread = ask_price - bid_price
        mid_price = (bid_price + ask_price) / 2
        spread_pct = spread / mid_price
        
        validation_result["spread"] = spread
        validation_result["spread_pct"] = spread_pct
        
        # Check against threshold
        threshold = self.bid_ask_spread_thresholds.get(security_type, 0.02)
        spread_exceeds = spread_pct > threshold
        
        validation_result["spread_exceeds_threshold"] = spread_exceeds
        
        if spread_exceeds:
            validation_result["warnings"].append(f"Bid-ask spread {spread_pct:.2%} exceeds threshold {threshold:.2%}")
        
        return validation_result
    
    def detect_price_anomalies(self, security_id: str, current_price: float,
                              historical_prices: List[float],
                              security_type: SecurityType = SecurityType.EQUITY) -> Dict[str, Any]:
        """
        Detect price anomalies using statistical methods.
        
        Args:
            security_id: Security identifier
            current_price: Current market price
            historical_prices: List of historical prices
            security_type: Type of security
            
        Returns:
            Anomaly detection results
        """
        anomaly_result = {
            "anomalies_detected": [],
            "statistical_measures": {},
            "confidence_score": 1.0
        }
        
        if len(historical_prices) < 10:
            anomaly_result["warnings"] = ["Insufficient historical data for anomaly detection"]
            return anomaly_result
        
        # Calculate statistical measures
        mean_price = statistics.mean(historical_prices)
        std_price = statistics.stdev(historical_prices)
        median_price = statistics.median(historical_prices)
        
        anomaly_result["statistical_measures"] = {
            "mean": mean_price,
            "std": std_price,
            "median": median_price,
            "min": min(historical_prices),
            "max": max(historical_prices)
        }
        
        # Detect anomalies using z-score
        if std_price > 0:
            z_score = abs(current_price - mean_price) / std_price
            
            if z_score > 3:
                anomaly_result["anomalies_detected"].append({
                    "type": "statistical_outlier",
                    "description": f"Price is {z_score:.2f} standard deviations from mean",
                    "severity": "high",
                    "z_score": z_score
                })
                anomaly_result["confidence_score"] = 0.2
            elif z_score > 2:
                anomaly_result["anomalies_detected"].append({
                    "type": "statistical_outlier",
                    "description": f"Price is {z_score:.2f} standard deviations from mean",
                    "severity": "medium",
                    "z_score": z_score
                })
                anomaly_result["confidence_score"] = 0.5
        
        # Detect price gaps
        price_change_pct = abs(current_price - historical_prices[-1]) / historical_prices[-1]
        if price_change_pct > 0.1:  # 10% change
            anomaly_result["anomalies_detected"].append({
                "type": "price_gap",
                "description": f"Price changed by {price_change_pct:.2%} from previous",
                "severity": "medium",
                "change_pct": price_change_pct
            })
            anomaly_result["confidence_score"] = min(anomaly_result["confidence_score"], 0.7)
        
        return anomaly_result
    
    def calculate_price_volatility(self, prices: List[float], window: int = 20) -> float:
        """
        Calculate price volatility using rolling standard deviation.
        
        Args:
            prices: List of historical prices
            window: Rolling window size
            
        Returns:
            Volatility measure
        """
        if len(prices) < window:
            return 0.0
        
        # Calculate rolling returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if len(returns) < window:
            return 0.0
        
        # Calculate rolling volatility
        volatilities = []
        for i in range(window, len(returns)):
            window_returns = returns[i-window:i]
            volatility = statistics.stdev(window_returns)
            volatilities.append(volatility)
        
        return statistics.mean(volatilities) if volatilities else 0.0
    
    def validate_price_consistency(self, prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate consistency of multiple prices for the same security.
        
        Args:
            prices: List of price dictionaries with keys: price, source, timestamp
            
        Returns:
            Consistency validation results
        """
        consistency_result = {
            "is_consistent": True,
            "inconsistencies": [],
            "price_range": {},
            "suggested_price": None
        }
        
        if len(prices) < 2:
            return consistency_result
        
        # Extract prices
        price_values = [p["price"] for p in prices]
        min_price = min(price_values)
        max_price = max(price_values)
        mean_price = statistics.mean(price_values)
        
        consistency_result["price_range"] = {
            "min": min_price,
            "max": max_price,
            "mean": mean_price,
            "range_pct": (max_price - min_price) / mean_price if mean_price > 0 else 0
        }
        
        # Check for significant price differences
        price_range_pct = consistency_result["price_range"]["range_pct"]
        if price_range_pct > 0.01:  # 1% range
            consistency_result["is_consistent"] = False
            consistency_result["inconsistencies"].append({
                "type": "price_range",
                "description": f"Price range is {price_range_pct:.2%}",
                "severity": "medium"
            })
        
        # Suggest best price (could be weighted by source reliability)
        consistency_result["suggested_price"] = mean_price
        
        return consistency_result
    
    def update_price_history(self, security_id: str, price: float, timestamp: datetime):
        """
        Update price history for a security.
        
        Args:
            security_id: Security identifier
            price: Market price
            timestamp: Price timestamp
        """
        if security_id not in self.price_history:
            self.price_history[security_id] = []
        
        self.price_history[security_id].append({
            "price": price,
            "timestamp": timestamp
        })
        
        # Keep only last 1000 prices
        if len(self.price_history[security_id]) > 1000:
            self.price_history[security_id] = self.price_history[security_id][-1000:]
    
    def get_price_history(self, security_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get price history for a security.
        
        Args:
            security_id: Security identifier
            days: Number of days of history to retrieve
            
        Returns:
            List of price history entries
        """
        if security_id not in self.price_history:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [entry for entry in self.price_history[security_id] 
                if entry["timestamp"] >= cutoff_date]


# Global validator instance
market_price_validator = MarketPriceValidator()


def validate_price(security_id: str, price: float, reference_price: float,
                  security_type: SecurityType = SecurityType.EQUITY,
                  tolerance_type: PriceToleranceType = PriceToleranceType.PERCENTAGE) -> Dict[str, Any]:
    """Validate a market price."""
    return market_price_validator.validate_price(security_id, price, reference_price, security_type, tolerance_type)


def validate_bid_ask_spread(bid_price: float, ask_price: float,
                           security_type: SecurityType = SecurityType.EQUITY) -> Dict[str, Any]:
    """Validate bid-ask spread."""
    return market_price_validator.validate_bid_ask_spread(bid_price, ask_price, security_type)


def detect_price_anomalies(security_id: str, current_price: float,
                          historical_prices: List[float],
                          security_type: SecurityType = SecurityType.EQUITY) -> Dict[str, Any]:
    """Detect price anomalies."""
    return market_price_validator.detect_price_anomalies(security_id, current_price, historical_prices, security_type)


def calculate_price_volatility(prices: List[float], window: int = 20) -> float:
    """Calculate price volatility."""
    return market_price_validator.calculate_price_volatility(prices, window) 
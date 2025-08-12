"""
FX Rate Processing Service for FS Reconciliation Agents.

This module implements foreign exchange rate processing, validation,
and calculations for multi-currency transactions.
"""

import logging
from datetime import datetime, date
from typing import Union, Optional, Dict, Any, List, Tuple
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class FXRateSource(str, Enum):
    """FX rate sources."""
    
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    INTERNAL = "internal"
    MARKET_DATA = "market_data"
    CUSTODIAN = "custodian"
    BANK = "bank"


class FXRateType(str, Enum):
    """FX rate types."""
    
    SPOT = "spot"
    FORWARD = "forward"
    SWAP = "swap"
    CROSS = "cross"


class FXRateProcessor:
    """Processor for FX rate calculations and validation."""
    
    def __init__(self):
        """Initialize the FX rate processor."""
        self.rate_cache = {}
        self.tolerance_thresholds = {
            "spot": 0.001,      # 0.1% for spot rates
            "forward": 0.002,    # 0.2% for forward rates
            "cross": 0.003       # 0.3% for cross rates
        }
    
    def validate_fx_rate(self, base_currency: str, quote_currency: str, rate: float,
                         rate_type: FXRateType = FXRateType.SPOT,
                         tolerance: Optional[float] = None) -> Dict[str, Any]:
        """
        Validate an FX rate against expected ranges and market data.
        
        Args:
            base_currency: Base currency (e.g., 'USD')
            quote_currency: Quote currency (e.g., 'EUR')
            rate: FX rate to validate
            rate_type: Type of FX rate
            tolerance: Custom tolerance threshold
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggested_rate": None,
            "confidence_score": 1.0
        }
        
        # Basic validation
        if rate <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("FX rate must be positive")
            return validation_result
        
        if base_currency == quote_currency:
            if rate != 1.0:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Same currency rate must be 1.0")
            return validation_result
        
        # Check for extreme rates
        if rate > 1000 or rate < 0.001:
            validation_result["warnings"].append("FX rate is outside normal range")
            validation_result["confidence_score"] = 0.5
        
        # Get tolerance threshold
        if tolerance is None:
            tolerance = self.tolerance_thresholds.get(rate_type.value, 0.001)
        
        # Check against cached rates (if available)
        cache_key = f"{base_currency}_{quote_currency}_{rate_type.value}"
        if cache_key in self.rate_cache:
            cached_rate = self.rate_cache[cache_key]
            rate_diff = abs(rate - cached_rate) / cached_rate
            
            if rate_diff > tolerance:
                validation_result["warnings"].append(f"Rate differs from cached rate by {rate_diff:.2%}")
                validation_result["confidence_score"] = max(0.3, 1.0 - rate_diff)
                validation_result["suggested_rate"] = cached_rate
        
        return validation_result
    
    def calculate_cross_rate(self, rate1: float, rate2: float, 
                           currency1: str, currency2: str, currency3: str) -> float:
        """
        Calculate cross rate from two other rates.
        
        Args:
            rate1: First rate (currency1/currency2)
            rate2: Second rate (currency2/currency3)
            currency1: First currency
            currency2: Second currency
            currency3: Third currency
            
        Returns:
            Cross rate (currency1/currency3)
        """
        return rate1 * rate2
    
    def calculate_inverse_rate(self, rate: float) -> float:
        """
        Calculate inverse of an FX rate.
        
        Args:
            rate: Original FX rate
            
        Returns:
            Inverse rate
        """
        if rate == 0:
            raise ValueError("Cannot calculate inverse of zero rate")
        return 1.0 / rate
    
    def calculate_fx_gain_loss(self, original_amount: float, original_currency: str,
                              fx_rate_original: float, fx_rate_current: float,
                              base_currency: str = "USD") -> Dict[str, Any]:
        """
        Calculate FX gain/loss on a position.
        
        Args:
            original_amount: Original amount in original currency
            original_currency: Original currency
            fx_rate_original: FX rate at original time
            fx_rate_current: Current FX rate
            base_currency: Base currency for calculations
            
        Returns:
            FX gain/loss calculation results
        """
        # Convert to base currency
        original_base = original_amount * fx_rate_original
        current_base = original_amount * fx_rate_current
        
        # Calculate gain/loss
        fx_gain_loss = current_base - original_base
        fx_gain_loss_pct = (fx_gain_loss / original_base) if original_base != 0 else 0
        
        return {
            "original_amount": original_amount,
            "original_currency": original_currency,
            "original_base_amount": original_base,
            "current_base_amount": current_base,
            "fx_gain_loss": fx_gain_loss,
            "fx_gain_loss_pct": fx_gain_loss_pct,
            "base_currency": base_currency
        }
    
    def calculate_forward_rate(self, spot_rate: float, domestic_rate: float,
                              foreign_rate: float, time_to_maturity: float) -> float:
        """
        Calculate forward rate using interest rate parity.
        
        Args:
            spot_rate: Current spot rate
            domestic_rate: Domestic interest rate
            foreign_rate: Foreign interest rate
            time_to_maturity: Time to maturity in years
            
        Returns:
            Forward rate
        """
        rate_differential = domestic_rate - foreign_rate
        forward_rate = spot_rate * (1 + rate_differential * time_to_maturity)
        return forward_rate
    
    def calculate_swap_points(self, spot_rate: float, forward_rate: float) -> float:
        """
        Calculate swap points (forward premium/discount).
        
        Args:
            spot_rate: Spot rate
            forward_rate: Forward rate
            
        Returns:
            Swap points
        """
        return forward_rate - spot_rate
    
    def validate_rate_consistency(self, rates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate consistency of multiple FX rates.
        
        Args:
            rates: List of rate dictionaries with keys: base_currency, quote_currency, rate
            
        Returns:
            Consistency validation results
        """
        validation_result = {
            "is_consistent": True,
            "inconsistencies": [],
            "suggested_corrections": []
        }
        
        # Build rate matrix
        rate_matrix = {}
        for rate_info in rates:
            base = rate_info["base_currency"]
            quote = rate_info["quote_currency"]
            rate = rate_info["rate"]
            
            if base not in rate_matrix:
                rate_matrix[base] = {}
            rate_matrix[base][quote] = rate
        
        # Check triangular arbitrage opportunities
        currencies = list(rate_matrix.keys())
        for i, curr1 in enumerate(currencies):
            for j, curr2 in enumerate(currencies):
                if i == j:
                    continue
                for k, curr3 in enumerate(currencies):
                    if k == i or k == j:
                        continue
                    
                    # Check if we can form a triangle
                    if (curr1 in rate_matrix and curr2 in rate_matrix[curr1] and
                        curr2 in rate_matrix and curr3 in rate_matrix[curr2] and
                        curr1 in rate_matrix and curr3 in rate_matrix[curr1]):
                        
                        rate1 = rate_matrix[curr1][curr2]
                        rate2 = rate_matrix[curr2][curr3]
                        rate3 = rate_matrix[curr1][curr3]
                        
                        # Calculate cross rate
                        cross_rate = rate1 * rate2
                        
                        # Check for arbitrage opportunity
                        if abs(cross_rate - rate3) / rate3 > 0.001:  # 0.1% tolerance
                            validation_result["is_consistent"] = False
                            validation_result["inconsistencies"].append({
                                "triangle": f"{curr1}-{curr2}-{curr3}",
                                "expected_rate": cross_rate,
                                "actual_rate": rate3,
                                "difference": abs(cross_rate - rate3) / rate3
                            })
                            validation_result["suggested_corrections"].append({
                                "currency_pair": f"{curr1}/{curr3}",
                                "current_rate": rate3,
                                "suggested_rate": cross_rate
                            })
        
        return validation_result
    
    def get_rate_source_priority(self, source: FXRateSource) -> int:
        """
        Get priority score for rate source (lower is higher priority).
        
        Args:
            source: FX rate source
            
        Returns:
            Priority score
        """
        priorities = {
            FXRateSource.BLOOMBERG: 1,
            FXRateSource.REUTERS: 2,
            FXRateSource.MARKET_DATA: 3,
            FXRateSource.CUSTODIAN: 4,
            FXRateSource.BANK: 5,
            FXRateSource.INTERNAL: 6
        }
        return priorities.get(source, 999)
    
    def cache_rate(self, base_currency: str, quote_currency: str, rate: float,
                  rate_type: FXRateType = FXRateType.SPOT, source: FXRateSource = FXRateSource.INTERNAL,
                  timestamp: Optional[datetime] = None):
        """
        Cache an FX rate for future validation.
        
        Args:
            base_currency: Base currency
            quote_currency: Quote currency
            rate: FX rate
            rate_type: Type of rate
            source: Source of the rate
            timestamp: Timestamp of the rate
        """
        cache_key = f"{base_currency}_{quote_currency}_{rate_type.value}"
        self.rate_cache[cache_key] = {
            "rate": rate,
            "source": source,
            "timestamp": timestamp or datetime.utcnow(),
            "priority": self.get_rate_source_priority(source)
        }
    
    def get_best_rate(self, base_currency: str, quote_currency: str,
                     rate_type: FXRateType = FXRateType.SPOT) -> Optional[Dict[str, Any]]:
        """
        Get the best available rate for a currency pair.
        
        Args:
            base_currency: Base currency
            quote_currency: Quote currency
            rate_type: Type of rate
            
        Returns:
            Best rate information or None if not available
        """
        cache_key = f"{base_currency}_{quote_currency}_{rate_type.value}"
        if cache_key in self.rate_cache:
            return self.rate_cache[cache_key]
        return None
    
    def calculate_multi_currency_position(self, positions: List[Dict[str, Any]],
                                       base_currency: str = "USD") -> Dict[str, Any]:
        """
        Calculate total position value in base currency.
        
        Args:
            positions: List of position dictionaries with keys: amount, currency, fx_rate
            base_currency: Base currency for calculations
            
        Returns:
            Multi-currency position calculation results
        """
        total_base_value = 0.0
        currency_positions = {}
        
        for position in positions:
            amount = position["amount"]
            currency = position["currency"]
            fx_rate = position["fx_rate"]
            
            base_value = amount * fx_rate
            total_base_value += base_value
            
            if currency not in currency_positions:
                currency_positions[currency] = 0.0
            currency_positions[currency] += amount
        
        return {
            "total_base_value": total_base_value,
            "base_currency": base_currency,
            "currency_positions": currency_positions,
            "number_of_currencies": len(currency_positions)
        }


# Global processor instance
fx_rate_processor = FXRateProcessor()


def validate_fx_rate(base_currency: str, quote_currency: str, rate: float,
                     rate_type: FXRateType = FXRateType.SPOT,
                     tolerance: Optional[float] = None) -> Dict[str, Any]:
    """Validate an FX rate."""
    return fx_rate_processor.validate_fx_rate(base_currency, quote_currency, rate, rate_type, tolerance)


def calculate_fx_gain_loss(original_amount: float, original_currency: str,
                          fx_rate_original: float, fx_rate_current: float,
                          base_currency: str = "USD") -> Dict[str, Any]:
    """Calculate FX gain/loss on a position."""
    return fx_rate_processor.calculate_fx_gain_loss(
        original_amount, original_currency, fx_rate_original, fx_rate_current, base_currency
    )


def calculate_forward_rate(spot_rate: float, domestic_rate: float,
                          foreign_rate: float, time_to_maturity: float) -> float:
    """Calculate forward rate using interest rate parity."""
    return fx_rate_processor.calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, time_to_maturity)


def validate_rate_consistency(rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate consistency of multiple FX rates."""
    return fx_rate_processor.validate_rate_consistency(rates) 
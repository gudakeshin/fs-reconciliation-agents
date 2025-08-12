"""
Fixed Income Calculations Service for FS Reconciliation Agents.

This module implements fixed income calculations including coupon payments,
accrued interest, yield calculations, and bond pricing.
"""

import logging
from datetime import datetime, date
from typing import Union, Optional, Dict, Any, List
from decimal import Decimal
from enum import Enum

from .day_count_conventions import DayCountConvention, calculate_days, calculate_year_fraction

logger = logging.getLogger(__name__)


class CouponFrequency(str, Enum):
    """Coupon payment frequencies."""
    
    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    ZERO_COUPON = "zero_coupon"


class FixedIncomeCalculator:
    """Calculator for fixed income instruments."""
    
    def __init__(self):
        """Initialize the fixed income calculator."""
        self.frequency_multipliers = {
            CouponFrequency.ANNUAL: 1,
            CouponFrequency.SEMI_ANNUAL: 2,
            CouponFrequency.QUARTERLY: 4,
            CouponFrequency.MONTHLY: 12,
            CouponFrequency.ZERO_COUPON: 0
        }
    
    def calculate_coupon_payment(self, face_value: float, coupon_rate: float, 
                                frequency: CouponFrequency) -> float:
        """
        Calculate the coupon payment amount.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            frequency: Coupon payment frequency
            
        Returns:
            Coupon payment amount
        """
        if frequency == CouponFrequency.ZERO_COUPON:
            return 0.0
        
        multiplier = self.frequency_multipliers[frequency]
        return (face_value * coupon_rate) / multiplier
    
    def calculate_accrued_interest(self, face_value: float, coupon_rate: float,
                                  last_coupon_date: Union[datetime, date],
                                  settlement_date: Union[datetime, date],
                                  next_coupon_date: Union[datetime, date],
                                  day_count_convention: DayCountConvention = DayCountConvention.ACTUAL_ACTUAL) -> float:
        """
        Calculate accrued interest for a bond.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            last_coupon_date: Date of last coupon payment
            settlement_date: Settlement date
            next_coupon_date: Date of next coupon payment
            day_count_convention: Day count convention to use
            
        Returns:
            Accrued interest amount
        """
        # Calculate days since last coupon
        days_since_last = calculate_days(last_coupon_date, settlement_date, day_count_convention)
        
        # Calculate days in coupon period
        days_in_period = calculate_days(last_coupon_date, next_coupon_date, day_count_convention)
        
        # Calculate accrued interest
        if days_in_period > 0:
            accrued_fraction = days_since_last / days_in_period
            annual_coupon = face_value * coupon_rate
            accrued_interest = annual_coupon * accrued_fraction
            return accrued_interest
        else:
            return 0.0
    
    def calculate_clean_price(self, dirty_price: float, accrued_interest: float) -> float:
        """
        Calculate clean price from dirty price.
        
        Args:
            dirty_price: Dirty price (including accrued interest)
            accrued_interest: Accrued interest amount
            
        Returns:
            Clean price
        """
        return dirty_price - accrued_interest
    
    def calculate_dirty_price(self, clean_price: float, accrued_interest: float) -> float:
        """
        Calculate dirty price from clean price.
        
        Args:
            clean_price: Clean price (excluding accrued interest)
            accrued_interest: Accrued interest amount
            
        Returns:
            Dirty price
        """
        return clean_price + accrued_interest
    
    def calculate_yield_to_maturity(self, face_value: float, coupon_rate: float,
                                   current_price: float, time_to_maturity: float,
                                   frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
                                   tolerance: float = 1e-6, max_iterations: int = 100) -> float:
        """
        Calculate yield to maturity using Newton-Raphson method.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            current_price: Current market price
            time_to_maturity: Time to maturity in years
            frequency: Coupon payment frequency
            tolerance: Convergence tolerance
            max_iterations: Maximum iterations for convergence
            
        Returns:
            Yield to maturity (as decimal)
        """
        # Initial guess: coupon rate
        ytm = coupon_rate
        
        for iteration in range(max_iterations):
            # Calculate present value with current YTM
            pv = self._calculate_present_value(face_value, coupon_rate, ytm, time_to_maturity, frequency)
            
            # Calculate derivative (modified duration approximation)
            pv_up = self._calculate_present_value(face_value, coupon_rate, ytm + 0.0001, time_to_maturity, frequency)
            derivative = (pv_up - pv) / 0.0001
            
            # Newton-Raphson update
            new_ytm = ytm - (pv - current_price) / derivative
            
            # Check convergence
            if abs(new_ytm - ytm) < tolerance:
                return new_ytm
            
            ytm = new_ytm
        
        logger.warning(f"YTM calculation did not converge after {max_iterations} iterations")
        return ytm
    
    def _calculate_present_value(self, face_value: float, coupon_rate: float, ytm: float,
                                time_to_maturity: float, frequency: CouponFrequency) -> float:
        """Calculate present value of bond cash flows."""
        if frequency == CouponFrequency.ZERO_COUPON:
            return face_value / ((1 + ytm) ** time_to_maturity)
        
        multiplier = self.frequency_multipliers[frequency]
        coupon_payment = self.calculate_coupon_payment(face_value, coupon_rate, frequency)
        periods = time_to_maturity * multiplier
        rate_per_period = ytm / multiplier
        
        # Present value of coupon payments
        if rate_per_period > 0:
            pv_coupons = coupon_payment * (1 - (1 + rate_per_period) ** (-periods)) / rate_per_period
        else:
            pv_coupons = coupon_payment * periods
        
        # Present value of face value
        pv_face = face_value / ((1 + rate_per_period) ** periods)
        
        return pv_coupons + pv_face
    
    def calculate_modified_duration(self, face_value: float, coupon_rate: float,
                                   current_price: float, time_to_maturity: float,
                                   frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
                                   ytm: Optional[float] = None) -> float:
        """
        Calculate modified duration.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            current_price: Current market price
            time_to_maturity: Time to maturity in years
            frequency: Coupon payment frequency
            ytm: Yield to maturity (if None, will be calculated)
            
        Returns:
            Modified duration
        """
        if ytm is None:
            ytm = self.calculate_yield_to_maturity(face_value, coupon_rate, current_price, time_to_maturity, frequency)
        
        # Calculate price with slightly higher yield
        price_up = self._calculate_present_value(face_value, coupon_rate, ytm + 0.0001, time_to_maturity, frequency)
        
        # Calculate price with slightly lower yield
        price_down = self._calculate_present_value(face_value, coupon_rate, ytm - 0.0001, time_to_maturity, frequency)
        
        # Modified duration = -(dP/dy) / P
        modified_duration = -(price_up - price_down) / (2 * 0.0001 * current_price)
        
        return modified_duration
    
    def calculate_convexity(self, face_value: float, coupon_rate: float,
                           current_price: float, time_to_maturity: float,
                           frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
                           ytm: Optional[float] = None) -> float:
        """
        Calculate convexity.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            current_price: Current market price
            time_to_maturity: Time to maturity in years
            frequency: Coupon payment frequency
            ytm: Yield to maturity (if None, will be calculated)
            
        Returns:
            Convexity
        """
        if ytm is None:
            ytm = self.calculate_yield_to_maturity(face_value, coupon_rate, current_price, time_to_maturity, frequency)
        
        # Calculate price with higher yield
        price_up = self._calculate_present_value(face_value, coupon_rate, ytm + 0.0001, time_to_maturity, frequency)
        
        # Calculate price with lower yield
        price_down = self._calculate_present_value(face_value, coupon_rate, ytm - 0.0001, time_to_maturity, frequency)
        
        # Calculate price at current yield
        price_current = self._calculate_present_value(face_value, coupon_rate, ytm, time_to_maturity, frequency)
        
        # Convexity = (d²P/dy²) / P
        convexity = (price_up + price_down - 2 * price_current) / (0.0001 ** 2 * current_price)
        
        return convexity
    
    def calculate_coupon_dates(self, issue_date: Union[datetime, date], maturity_date: Union[datetime, date],
                              frequency: CouponFrequency) -> List[date]:
        """
        Calculate coupon payment dates.
        
        Args:
            issue_date: Bond issue date
            maturity_date: Bond maturity date
            frequency: Coupon payment frequency
            
        Returns:
            List of coupon payment dates
        """
        if frequency == CouponFrequency.ZERO_COUPON:
            return [maturity_date]
        
        multiplier = self.frequency_multipliers[frequency]
        months_between_payments = 12 // multiplier
        
        coupon_dates = []
        current_date = issue_date
        
        while current_date < maturity_date:
            coupon_dates.append(current_date)
            
            # Add months to current date
            year = current_date.year + (current_date.month + months_between_payments - 1) // 12
            month = ((current_date.month + months_between_payments - 1) % 12) + 1
            day = min(current_date.day, self._days_in_month(year, month))
            
            current_date = date(year, month, day)
        
        # Add maturity date if not already included
        if maturity_date not in coupon_dates:
            coupon_dates.append(maturity_date)
        
        return coupon_dates
    
    def _days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month."""
        if month == 2:
            return 29 if self._is_leap_year(year) else 28
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 31
    
    def _is_leap_year(self, year: int) -> bool:
        """Check if a year is a leap year."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    
    def validate_bond_parameters(self, face_value: float, coupon_rate: float,
                                issue_date: Union[datetime, date], maturity_date: Union[datetime, date],
                                frequency: CouponFrequency) -> Dict[str, Any]:
        """
        Validate bond parameters and return validation results.
        
        Args:
            face_value: Face value of the bond
            coupon_rate: Annual coupon rate (as decimal)
            issue_date: Bond issue date
            maturity_date: Bond maturity date
            frequency: Coupon payment frequency
            
        Returns:
            Validation results dictionary
        """
        errors = []
        warnings = []
        
        # Validate face value
        if face_value <= 0:
            errors.append("Face value must be positive")
        
        # Validate coupon rate
        if coupon_rate < 0:
            errors.append("Coupon rate cannot be negative")
        elif coupon_rate > 1:
            warnings.append("Coupon rate is greater than 100%")
        
        # Validate dates
        if issue_date >= maturity_date:
            errors.append("Issue date must be before maturity date")
        
        # Validate frequency
        if frequency not in CouponFrequency:
            errors.append(f"Invalid coupon frequency: {frequency}")
        
        # Calculate bond characteristics
        coupon_dates = self.calculate_coupon_dates(issue_date, maturity_date, frequency)
        coupon_payment = self.calculate_coupon_payment(face_value, coupon_rate, frequency)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "coupon_dates": coupon_dates,
            "coupon_payment": coupon_payment,
            "number_of_payments": len(coupon_dates)
        }


# Global calculator instance
fixed_income_calculator = FixedIncomeCalculator()


def calculate_coupon_payment(face_value: float, coupon_rate: float, frequency: CouponFrequency) -> float:
    """Calculate coupon payment amount."""
    return fixed_income_calculator.calculate_coupon_payment(face_value, coupon_rate, frequency)


def calculate_accrued_interest(face_value: float, coupon_rate: float,
                              last_coupon_date: Union[datetime, date],
                              settlement_date: Union[datetime, date],
                              next_coupon_date: Union[datetime, date],
                              day_count_convention: DayCountConvention = DayCountConvention.ACTUAL_ACTUAL) -> float:
    """Calculate accrued interest for a bond."""
    return fixed_income_calculator.calculate_accrued_interest(
        face_value, coupon_rate, last_coupon_date, settlement_date, next_coupon_date, day_count_convention
    )


def calculate_yield_to_maturity(face_value: float, coupon_rate: float,
                               current_price: float, time_to_maturity: float,
                               frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL) -> float:
    """Calculate yield to maturity."""
    return fixed_income_calculator.calculate_yield_to_maturity(
        face_value, coupon_rate, current_price, time_to_maturity, frequency
    )


def validate_bond_parameters(face_value: float, coupon_rate: float,
                            issue_date: Union[datetime, date], maturity_date: Union[datetime, date],
                            frequency: CouponFrequency) -> Dict[str, Any]:
    """Validate bond parameters."""
    return fixed_income_calculator.validate_bond_parameters(
        face_value, coupon_rate, issue_date, maturity_date, frequency
    ) 
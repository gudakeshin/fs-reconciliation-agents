"""
Day Count Conventions Service for FS Reconciliation Agents.

This module implements various day count conventions used in fixed income
calculations, including Actual/Actual, 30/360, Actual/365, and others.
"""

import logging
from datetime import datetime, date
from typing import Union, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DayCountConvention(str, Enum):
    """Day count conventions for fixed income calculations."""
    
    ACTUAL_ACTUAL = "actual_actual"  # Actual/Actual (ISDA)
    ACTUAL_365 = "actual_365"        # Actual/365 (Fixed)
    ACTUAL_360 = "actual_360"        # Actual/360
    THIRTY_360 = "30_360"            # 30/360 (Bond Basis)
    THIRTY_365 = "30_365"            # 30/365
    ACTUAL_ACTUAL_LEAP = "actual_actual_leap"  # Actual/Actual (Leap Year)


class DayCountCalculator:
    """Calculator for various day count conventions."""
    
    def __init__(self):
        """Initialize the day count calculator."""
        self.conventions = {
            DayCountConvention.ACTUAL_ACTUAL: self._actual_actual,
            DayCountConvention.ACTUAL_365: self._actual_365,
            DayCountConvention.ACTUAL_360: self._actual_360,
            DayCountConvention.THIRTY_360: self._thirty_360,
            DayCountConvention.THIRTY_365: self._thirty_365,
            DayCountConvention.ACTUAL_ACTUAL_LEAP: self._actual_actual_leap
        }
    
    def calculate_days(self, start_date: Union[datetime, date], end_date: Union[datetime, date], 
                      convention: DayCountConvention) -> int:
        """
        Calculate the number of days between two dates using the specified convention.
        
        Args:
            start_date: Start date
            end_date: End date
            convention: Day count convention to use
            
        Returns:
            Number of days according to the convention
        """
        if convention not in self.conventions:
            raise ValueError(f"Unsupported day count convention: {convention}")
        
        return self.conventions[convention](start_date, end_date)
    
    def calculate_year_fraction(self, start_date: Union[datetime, date], end_date: Union[datetime, date],
                               convention: DayCountConvention) -> float:
        """
        Calculate the year fraction between two dates using the specified convention.
        
        Args:
            start_date: Start date
            end_date: End date
            convention: Day count convention to use
            
        Returns:
            Year fraction as a decimal
        """
        days = self.calculate_days(start_date, end_date, convention)
        
        if convention == DayCountConvention.ACTUAL_365:
            return days / 365.0
        elif convention == DayCountConvention.ACTUAL_360:
            return days / 360.0
        elif convention == DayCountConvention.THIRTY_365:
            return days / 365.0
        elif convention == DayCountConvention.THIRTY_360:
            return days / 360.0
        elif convention in [DayCountConvention.ACTUAL_ACTUAL, DayCountConvention.ACTUAL_ACTUAL_LEAP]:
            return days / self._get_actual_days_in_year(start_date, end_date)
        else:
            raise ValueError(f"Unsupported convention for year fraction: {convention}")
    
    def _actual_actual(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """Actual/Actual (ISDA) day count convention."""
        return (end_date - start_date).days
    
    def _actual_365(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """Actual/365 (Fixed) day count convention."""
        return (end_date - start_date).days
    
    def _actual_360(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """Actual/360 day count convention."""
        return (end_date - start_date).days
    
    def _thirty_360(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """30/360 (Bond Basis) day count convention."""
        start_year = start_date.year
        start_month = start_date.month
        start_day = min(start_date.day, 30)
        
        end_year = end_date.year
        end_month = end_date.month
        end_day = min(end_date.day, 30)
        
        # Adjust end day if start day is 30 or 31
        if start_day == 30 or start_day == 31:
            if end_day == 31:
                end_day = 30
        
        days = (end_year - start_year) * 360 + (end_month - start_month) * 30 + (end_day - start_day)
        return days
    
    def _thirty_365(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """30/365 day count convention."""
        return self._thirty_360(start_date, end_date)
    
    def _actual_actual_leap(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """Actual/Actual (Leap Year) day count convention."""
        return (end_date - start_date).days
    
    def _get_actual_days_in_year(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> int:
        """Get the actual number of days in the year for Actual/Actual calculations."""
        # For Actual/Actual, we need to determine the appropriate year
        # This is a simplified implementation - in practice, this would be more complex
        year = start_date.year
        if self._is_leap_year(year):
            return 366
        else:
            return 365
    
    def _is_leap_year(self, year: int) -> bool:
        """Check if a year is a leap year."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    
    def get_convention_description(self, convention: DayCountConvention) -> str:
        """Get a description of the day count convention."""
        descriptions = {
            DayCountConvention.ACTUAL_ACTUAL: "Actual/Actual (ISDA) - Uses actual days and actual days in year",
            DayCountConvention.ACTUAL_365: "Actual/365 (Fixed) - Uses actual days divided by 365",
            DayCountConvention.ACTUAL_360: "Actual/360 - Uses actual days divided by 360",
            DayCountConvention.THIRTY_360: "30/360 (Bond Basis) - Assumes 30 days per month, 360 days per year",
            DayCountConvention.THIRTY_365: "30/365 - Assumes 30 days per month, 365 days per year",
            DayCountConvention.ACTUAL_ACTUAL_LEAP: "Actual/Actual (Leap Year) - Handles leap years correctly"
        }
        return descriptions.get(convention, "Unknown convention")


# Global calculator instance
day_count_calculator = DayCountCalculator()


def calculate_days(start_date: Union[datetime, date], end_date: Union[datetime, date], 
                  convention: DayCountConvention) -> int:
    """Calculate days between dates using specified convention."""
    return day_count_calculator.calculate_days(start_date, end_date, convention)


def calculate_year_fraction(start_date: Union[datetime, date], end_date: Union[datetime, date],
                          convention: DayCountConvention) -> float:
    """Calculate year fraction between dates using specified convention."""
    return day_count_calculator.calculate_year_fraction(start_date, end_date, convention)


def get_convention_description(convention: DayCountConvention) -> str:
    """Get description of day count convention."""
    return day_count_calculator.get_convention_description(convention) 
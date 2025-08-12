# Test Data Breaks Summary

This document describes the intentional breaks created in the test data files to test the reconciliation system's ability to detect and classify different types of breaks.

## Files Created

1. **`trades_source_a_comprehensive.csv`** - Source A with 50 rows of clean data
2. **`trades_source_b_with_breaks.csv`** - Source B with 50 rows including 5 intentional breaks

## Break Types Implemented

Based on the BRD requirements, the following 5 break types have been implemented with approximately 10% breaks (5 breaks out of 50 rows):

### 1. Market Price Differences (Row 1)
- **Source A**: Market Price = 150.25
- **Source B**: Market Price = 157.75
- **Difference**: +7.50 (5% increase)
- **Break Type**: `market_price_difference`

### 2. Fixed Income Coupon Payments (Row 2)
- **Source A**: Amount = 50,000.00
- **Source B**: Amount = 51,000.00
- **Difference**: +1,000.00 (2% increase)
- **Break Type**: `fixed_income_coupon`

### 3. Trade Date vs. Settlement Date (Row 3)
- **Source A**: Settlement Date = 2024-01-17
- **Source B**: Settlement Date = 2024-01-18
- **Difference**: +1 day
- **Break Type**: `trade_settlement_date`

### 4. FX Rate Errors (Row 4)
- **Source A**: FX Rate = 1.0000, Market Value = 25,000.00
- **Source B**: FX Rate = 1.0500, Market Value = 26,250.00
- **Difference**: +5% FX rate difference
- **Break Type**: `fx_rate_error`

### 5. Security ID Breaks (Row 5)
- **Source A**: CUSIP = 037833100
- **Source B**: CUSIP = 037833100 (same)
- **Source A**: SEDOL = 2046251
- **Source B**: SEDOL = 2046252 (different)
- **Difference**: Different SEDOL identifier
- **Break Type**: `security_id_break`

## Expected Reconciliation Results

When these files are uploaded to the reconciliation system, it should:

1. **Match 45 transactions** (90% match rate)
2. **Identify 5 breaks** (10% break rate)
3. **Classify breaks correctly** according to the break types above
4. **Generate AI analysis** for each break with detailed differences and workflow triggers
5. **Populate audit trail** with reconciliation activities

## Testing Instructions

1. Upload `trades_source_a_comprehensive.csv` as Source A
2. Upload `trades_source_b_with_breaks.csv` as Source B
3. Run the reconciliation process
4. Verify that 5 exceptions are identified
5. Check that each exception has:
   - Correct break type classification
   - Detailed differences captured
   - AI reasoning and suggested actions
   - Workflow triggers for resolution

## Break Distribution

- **Rows 1-5**: Each contains one of the 5 break types
- **Rows 6-50**: Clean matching data for baseline comparison
- **Total**: 5 breaks out of 50 rows = 10% break rate

This test data provides a comprehensive validation of the reconciliation system's ability to detect, classify, and provide intelligent analysis for all major break types identified in the BRD.

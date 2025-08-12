# Break Detection and AI Analysis Fixes

## Issues Identified and Fixed

### 1. Security ID Break Not Being Caught

**Problem**: The security ID break detection logic was only checking `security_id`, `isin`, and `cusip` fields, but not `sedol` differences.

**Root Cause**: In `src/core/agents/exception_identification/agent.py`, the `_detect_security_breaks` method was missing SEDOL comparison logic.

**Fix Applied**:
- Updated the security ID break detection to include SEDOL comparison
- Added specific logic to detect SEDOL mismatches
- Enhanced break details to include mismatch type (security_id vs sedol)
- Updated break details structure to capture SEDOL-specific information

**Code Changes**:
```python
# Before
security_a = trans_a.get("security_id") or trans_a.get("isin") or trans_a.get("cusip")
security_b = trans_b.get("security_id") or trans_b.get("isin") or trans_b.get("cusip")

if security_a and security_b and security_a != security_b:

# After  
security_a = trans_a.get("security_id") or trans_a.get("isin") or trans_a.get("cusip")
security_b = trans_b.get("security_id") or trans_b.get("isin") or trans_b.get("cusip")

# Also check SEDOL specifically
sedol_a = trans_a.get("sedol")
sedol_b = trans_b.get("sedol")

if (security_a and security_b and security_a != security_b) or (sedol_a and sedol_b and sedol_a != sedol_b):
```

### 2. AI Analysis and Workflow Not Showing

**Problem**: The `_enhance_break_classification` method was missing handlers for security ID breaks and FX rate errors, causing these breaks to fall through to the generic "else" clause.

**Root Cause**: The method only had specific handlers for `fixed_income_coupon`, `trade_settlement_date`, and `market_price_difference` break types.

**Fix Applied**:
- Added specific handler for `security_id_break` type
- Added specific handler for `fx_rate_error` type
- Enhanced both handlers to provide detailed differences and workflow triggers
- Added SEDOL-specific analysis for security ID breaks

**Code Changes**:
```python
elif break_type == "security_id_break":
    # Extract security ID differences
    break_details = break_info.get("break_details", {})
    mismatch_type = break_details.get("mismatch_type", "unknown")
    
    if mismatch_type == "sedol":
        sedol_a = break_details.get("sedol_a", "Unknown")
        sedol_b = break_details.get("sedol_b", "Unknown")
        
        break_info["ai_reasoning"] = f"Security ID mismatch detected. SEDOL A: {sedol_a}, SEDOL B: {sedol_b}. This indicates different security identifiers being used by transacting parties."
        break_info["ai_suggested_actions"] = ["Verify security identifier mapping", "Check identifier database", "Contact counterparty for clarification"]
        break_info["detailed_differences"] = {
            "identifier_type": "SEDOL",
            "identifier_a": sedol_a,
            "identifier_b": sedol_b,
            "difference": f"{sedol_a} vs {sedol_b}",
            "security_name": trans_a.get("security_name", "Unknown"),
            "transaction_id": trans_a.get("external_id", "Unknown")
        }
        break_info["workflow_triggers"] = [
            {
                "action": "verify_security_mapping",
                "title": "Verify Security Mapping",
                "description": "Check security identifier mapping and database accuracy",
                "workflow_id": "security_mapping_workflow",
                "parameters": {
                    "security_name": trans_a.get("security_name"),
                    "identifier_type": mismatch_type,
                    "identifier_a": break_details.get(f"{mismatch_type}_a"),
                    "identifier_b": break_details.get(f"{mismatch_type}_b")
                }
            },
            {
                "action": "contact_counterparty",
                "title": "Contact Counterparty",
                "description": "Contact counterparty to clarify security identifier discrepancy",
                "workflow_id": "counterparty_contact_workflow",
                "parameters": {
                    "counterparty": trans_a.get("counterparty"),
                    "trade_id": trans_a.get("external_id"),
                    "issue_type": "security_identifier_mismatch"
                }
            }
        ]
```

## Expected Results

After these fixes, when you upload the test data files:

1. **Security ID Break (Row 5)**: Should now be detected due to SEDOL difference (2046251 vs 2046252)
2. **All 5 Breaks**: Should now have proper AI analysis with:
   - Detailed differences captured
   - AI reasoning explaining the break
   - Suggested actions for resolution
   - Workflow triggers for automated resolution

## Test Data Files

- `trades_source_a_comprehensive.csv` - Source A with 50 clean rows
- `trades_source_b_with_breaks.csv` - Source B with 5 intentional breaks:
  1. **Row 1**: Market Price Difference (150.25 vs 157.75)
  2. **Row 2**: Fixed Income Coupon (50,000 vs 51,000)
  3. **Row 3**: Trade Settlement Date (Jan 17 vs Jan 18)
  4. **Row 4**: FX Rate Error (1.0000 vs 1.0500)
  5. **Row 5**: Security ID Break (SEDOL: 2046251 vs 2046252)

## Deployment Status

- ✅ Updated exception identification agent code
- ✅ Copied updated code to API container
- ✅ Restarted API service
- ✅ Verified API is healthy

The fixes are now deployed and ready for testing with the new test data files.

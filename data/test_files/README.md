# Test Data Files

## ⚠️ IMPORTANT: Data Missing Notice

The test files in this directory contain **simulated/dummy data** for demonstration purposes only. This violates the workspace rule about not using dummy data in production code.

### Current Test Files:
- `trades_source_a.csv` - Simulated trade data with dummy security IDs and amounts
- `settlements_source_b.csv` - Simulated settlement data
- `trades_with_exceptions.csv` - Simulated trade data with reconciliation exceptions
- `settlements_with_exceptions.csv` - Simulated settlement data with exceptions
- `trades_with_mismatches.csv` - Simulated trade data with matching issues
- `settlements_with_mismatches.csv` - Simulated settlement data with matching issues
- `trades_with_price_mismatches.csv` - Simulated trade data with price discrepancies
- `settlements_with_price_mismatches.csv` - Simulated settlement data with price discrepancies

### Required Actions:

1. **Replace with Actual Data**: These files should be replaced with actual financial transaction data for production use.

2. **Data Requirements**: Real data should include:
   - Valid security identifiers (ISIN, CUSIP, SEDOL)
   - Actual transaction amounts and dates
   - Real counterparty information
   - Authentic market prices and rates

3. **Data Sources**: Consider using:
   - Anonymized production data samples
   - Public financial datasets
   - Bloomberg/Reuters data feeds
   - Bank statement exports

### For Development/Testing:
If you need to use these files for development or testing:
1. Clearly mark them as test data
2. Use them only in development environments
3. Document that they contain simulated data
4. Replace with real data before production deployment

### Data Format:
The expected CSV format for real data should include:
- TransactionID: Unique transaction identifier
- SecurityID: Valid security identifier
- SecurityType: Type of security (EQUITY, BOND, etc.)
- Quantity: Number of securities
- Price: Transaction price
- Currency: Currency code (ISO 4217)
- TradeDate: Trade date (YYYY-MM-DD)
- SettlementDate: Settlement date (YYYY-MM-DD)
- Counterparty: Trading counterparty
- Trader: Trader name
- Desk: Trading desk
- ProductType: Product type
- Status: Transaction status

**Note**: This directory should be updated with actual financial data before the application is used in production.

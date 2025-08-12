#!/usr/bin/env python3
"""
Script to enhance existing exceptions with AI analysis.
This script will add AI reasoning and suggested actions to exceptions that don't have them.
"""

import asyncio
import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import select
from src.core.services.data_services.database import get_db_session
from src.core.models.break_types.reconciliation_break import ReconciliationException
from src.core.agents.exception_identification.agent import ExceptionIdentificationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def enhance_existing_exceptions():
    """Add AI analysis to existing exceptions that don't have it."""
    try:
        async with get_db_session() as session:
            # Get exceptions without AI reasoning
            query = select(ReconciliationException).where(
                ReconciliationException.ai_reasoning.is_(None)
            )
            result = await session.execute(query)
            exceptions = result.scalars().all()
            
            if not exceptions:
                logger.info("No exceptions found that need AI enhancement")
                return
            
            logger.info(f"Found {len(exceptions)} exceptions to enhance with AI analysis")
            
            # Initialize the exception identification agent
            agent = ExceptionIdentificationAgent()
            
            enhanced_count = 0
            for exception in exceptions:
                try:
                    logger.info(f"Enhancing exception {exception.id} ({exception.break_type})")
                    
                    # Create mock transaction data for analysis
                    transaction_data = {
                        "external_id": f"tx_{exception.id}",
                        "amount": float(exception.break_amount) if exception.break_amount else 0.0,
                        "currency": exception.break_currency or "USD",
                        "break_type": exception.break_type,
                        "severity": exception.severity,
                        "transaction_id": str(exception.transaction_id)
                    }
                    
                    # Generate AI analysis based on break type
                    if exception.break_type == "fixed_income_coupon":
                        # Mock transaction data for coupon analysis
                        trans_a = {
                            "external_id": f"tx_a_{exception.id}",
                            "amount": float(exception.break_amount) if exception.break_amount else 0.0,
                            "currency": exception.break_currency or "USD",
                            "security_id": "BOND001",
                            "trade_date": "2024-01-15"
                        }
                        trans_b = {
                            "external_id": f"tx_b_{exception.id}",
                            "amount": 0.0,
                            "currency": exception.break_currency or "USD",
                            "security_id": "BOND001",
                            "trade_date": "2024-01-15"
                        }
                        
                        analysis = await agent._analyze_coupon_break_detailed(
                            trans_a, trans_b, 
                            float(exception.break_amount) if exception.break_amount else 0.0, 
                            0.0
                        )
                        
                        exception.ai_reasoning = analysis.get("reasoning", "Coupon payment discrepancy detected")
                        exception.ai_suggested_actions = analysis.get("recommendations", [
                            "Verify coupon calculation",
                            "Check payment dates",
                            "Review accrued interest"
                        ])
                        
                    elif exception.break_type == "trade_settlement_date":
                        exception.ai_reasoning = "Trade vs settlement date mismatch detected. This may indicate timing differences between trade execution and settlement."
                        exception.ai_suggested_actions = [
                            "Verify trade execution date",
                            "Check settlement date accuracy",
                            "Review market conventions"
                        ]
                        
                    elif exception.break_type == "market_price_difference":
                        exception.ai_reasoning = "Market price difference detected between sources. This may indicate data timing or source accuracy issues."
                        exception.ai_suggested_actions = [
                            "Verify price source accuracy",
                            "Check price timestamp",
                            "Review market data quality"
                        ]
                        
                    else:
                        # Generic analysis for other break types
                        exception.ai_reasoning = f"{exception.break_type.replace('_', ' ').title()} break detected. Manual review required."
                        exception.ai_suggested_actions = [
                            "Review transaction details",
                            "Verify data accuracy",
                            "Contact counterparty if needed"
                        ]
                    
                    enhanced_count += 1
                    logger.info(f"Enhanced exception {exception.id}")
                    
                except Exception as e:
                    logger.error(f"Error enhancing exception {exception.id}: {e}")
                    continue
            
            # Commit all changes
            await session.commit()
            logger.info(f"Successfully enhanced {enhanced_count} exceptions with AI analysis")
            
    except Exception as e:
        logger.error(f"Error in enhance_existing_exceptions: {e}")
        raise

async def main():
    """Main function."""
    logger.info("Starting exception enhancement process...")
    await enhance_existing_exceptions()
    logger.info("Exception enhancement process completed")

if __name__ == "__main__":
    asyncio.run(main())

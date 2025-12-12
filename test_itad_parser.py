#!/usr/bin/env python3
"""
Test script for ITAD price parser
Tests on 1-2 AppIDs to verify API integration and data format
"""
import sys
import logging
from pathlib import Path
import config
from itad_price_parser import ITADPriceParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Test ITAD parser on sample app IDs"""
    
    # Test with popular games
    # 730 = Counter-Strike: Global Offensive
    # 440 = Team Fortress 2
    test_app_ids = [730, 440]
    
    logger.info("=" * 60)
    logger.info("ITAD Price Parser Test")
    logger.info("=" * 60)
    logger.info(f"Testing with App IDs: {test_app_ids}")
    
    # Check API key
    if not config.ITAD_API_KEY:
        logger.warning("⚠️  ITAD_API_KEY not set in config or environment")
        logger.info("To get API key:")
        logger.info("1. Register at https://isthereanydeal.com/app/")
        logger.info("2. Get your API key")
        logger.info("3. Set ITAD_API_KEY environment variable or add to config.py")
        logger.info("")
        logger.info("Continuing test without API key (may fail)...")
    
    # Initialize parser
    parser = ITADPriceParser()
    
    # Parse price history
    logger.info("Starting price history parsing...")
    stats = parser.parse_price_history(test_app_ids, batch_number=1)
    
    # Print results
    logger.info("=" * 60)
    logger.info("Test Results:")
    logger.info(f"  Processed records: {stats['processed']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info("=" * 60)
    
    # Check output files
    output_dir = config.DATA_DIR / "itad_price_history"
    csv_files = list(output_dir.glob("price_history_batch_1.csv"))
    
    if csv_files:
        csv_file = csv_files[0]
        # Count lines in file
        with open(csv_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f) - 1  # Exclude header
        logger.info(f"\nGenerated CSV file: {csv_file.name}")
        logger.info(f"  Total records: {line_count}")
        
        # Show sample data
        logger.info("\nSample data:")
        logger.info("-" * 60)
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:11]  # Header + 10 rows
            for line in lines:
                logger.info(f"  {line.strip()}")
    else:
        logger.warning("No CSV files generated. Check API key and API responses.")
    
    logger.info("\nTest completed!")


if __name__ == "__main__":
    main()


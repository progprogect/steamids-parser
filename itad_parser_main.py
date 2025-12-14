"""
Main ITAD Price Parser - Entry point for parsing
Supports checkpoint/resume and progress tracking
"""
import logging
import signal
import sys
from pathlib import Path
from typing import List
import config
from itad_price_parser_hybrid import ITADPriceParserHybrid
from checkpoint import CheckpointManager
from database import Database
from progress import ProgressTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ITADParserMain:
    """Main ITAD parser orchestrator"""
    
    def __init__(self, app_ids_file: Path = None):
        """
        Initialize ITAD parser
        
        Args:
            app_ids_file: Path to file with app IDs (one per line)
        """
        self.app_ids_file = app_ids_file or config.APP_IDS_FILE
        self.database = Database()
        self.checkpoint_manager = CheckpointManager(self.database)
        self.parser = ITADPriceParserHybrid()
        self.progress_tracker = ProgressTracker(self.checkpoint_manager)
        self.running = True
        
        # Setup signal handlers
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # Signal handlers can only be set in main thread
            logger.debug("Signal handlers skipped (running in thread)")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        logger.info("Received interrupt signal, shutting down gracefully...")
        self.running = False
        self.parser.running = False
        try:
            self.checkpoint_manager.save_checkpoint()
            logger.info("Checkpoint saved. You can resume parsing by running again.")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def load_app_ids(self) -> List[int]:
        """Load app IDs from file"""
        if not self.app_ids_file.exists():
            raise FileNotFoundError(f"App IDs file not found: {self.app_ids_file}")
        
        app_ids = []
        with open(self.app_ids_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    app_ids.append(int(line))
        
        logger.info(f"Loaded {len(app_ids)} app IDs from {self.app_ids_file}")
        return app_ids
    
    def run(self):
        """Run ITAD parser"""
        try:
            # Load app IDs
            app_ids = self.load_app_ids()
            
            # Initialize app IDs in database
            self.checkpoint_manager.initialize_app_ids(app_ids)
            
            # Get pending app IDs only from loaded list (for resume support)
            # Filter to only process the app_ids we loaded
            logger.info(f"Getting pending app IDs from database...")
            all_pending = self.checkpoint_manager.get_pending_itad_app_ids()
            logger.info(f"Found {len(all_pending)} pending app IDs in database")
            logger.info(f"Loaded {len(app_ids)} app IDs from file")
            
            pending_app_ids = [app_id for app_id in all_pending if app_id in app_ids]
            logger.info(f"After filtering: {len(pending_app_ids)} app IDs to process")
            
            if not pending_app_ids:
                logger.warning(f"No pending app IDs found in loaded list. All apps already processed.")
                logger.warning(f"Loaded app IDs: {len(app_ids)}, Pending in DB: {len(all_pending)}")
                logger.warning(f"First 10 loaded: {app_ids[:10]}")
                logger.warning(f"First 10 pending: {all_pending[:10]}")
                return
            
            logger.info(f"Processing {len(pending_app_ids)} app IDs (from {len(app_ids)} loaded)")
            
            # Split into batches
            batch_size = config.ITAD_BATCH_SIZE
            batches = [
                pending_app_ids[i:i + batch_size]
                for i in range(0, len(pending_app_ids), batch_size)
            ]
            
            total_batches = len(batches)
            logger.info(f"Split into {total_batches} batches of {batch_size} app IDs")
            
            # Process batches
            total_processed = 0
            total_errors = 0
            
            for batch_num, batch_app_ids in enumerate(batches, 1):
                if not self.running:
                    logger.info("Parser stopped by user")
                    break
                
                logger.info(f"\n{'='*70}")
                logger.info(f"Processing batch {batch_num}/{total_batches}")
                logger.info(f"{'='*70}")
                
                try:
                    # Mark apps as processing
                    for app_id in batch_app_ids:
                        self.checkpoint_manager.mark_itad_processing(app_id)
                    
                    # Parse batch (checkpoint is updated inside parse_price_history_batch)
                    stats = self.parser.parse_price_history_batch(batch_app_ids, batch_num)
                    
                    total_processed += stats.get('processed', 0)
                    total_errors += stats.get('errors', 0)
                    
                    # Save checkpoint
                    self.checkpoint_manager.save_checkpoint()
                    
                    # Display progress
                    self.progress_tracker.display_statistics(force=True)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                    total_errors += len(batch_app_ids)
                    
                    # Mark batch as error
                    for app_id in batch_app_ids:
                        self.checkpoint_manager.mark_itad_error(app_id, str(e))
                    
                    # Save checkpoint even on error
                    self.checkpoint_manager.save_checkpoint()
            
            # Final summary
            logger.info(f"\n{'='*70}")
            logger.info("PARSING COMPLETED")
            logger.info(f"{'='*70}")
            logger.info(f"Total processed: {total_processed}")
            logger.info(f"Total errors: {total_errors}")
            logger.info(f"{'='*70}\n")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.database.close()


def main():
    """Main entry point"""
    parser = ITADParserMain()
    parser.run()


if __name__ == "__main__":
    main()


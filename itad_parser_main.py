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
            
            # Reset apps stuck in 'itad_processing' status (from previous interrupted runs)
            reset_count = self.checkpoint_manager.reset_stuck_processing_apps()
            if reset_count > 0:
                logger.info(f"Reset {reset_count} apps from 'itad_processing' to 'pending' for retry")
            
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
            batches_completed = 0
            
            for batch_num, batch_app_ids in enumerate(batches, 1):
                if not self.running:
                    logger.info("Parser stopped by user signal (self.running = False)")
                    logger.info(f"Processed {batch_num - 1}/{total_batches} batches before stop")
                    break
                
                logger.info(f"\n{'='*70}")
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_app_ids)} app IDs)")
                logger.info(f"{'='*70}")
                
                try:
                    # Mark apps as processing
                    for app_id in batch_app_ids:
                        self.checkpoint_manager.mark_itad_processing(app_id)
                    
                    # Parse batch (checkpoint is updated inside parse_price_history_batch)
                    stats = self.parser.parse_price_history_batch(batch_app_ids, batch_num)
                    
                    batch_processed = stats.get('processed', 0)
                    batch_errors = stats.get('errors', 0)
                    
                    total_processed += batch_processed
                    total_errors += batch_errors
                    
                    logger.info(f"Batch {batch_num} summary: {batch_processed} processed, {batch_errors} errors")
                    
                    # Save checkpoint
                    self.checkpoint_manager.save_checkpoint()
                    
                    # Display progress
                    self.progress_tracker.display_statistics(force=True)
                    
                    batches_completed = batch_num
                    
                    # Check if parser was stopped during batch processing
                    if not self.running:
                        logger.warning("Parser was stopped during batch processing")
                        break
                    
                except KeyboardInterrupt:
                    logger.info("Parser interrupted by user (KeyboardInterrupt)")
                    self.running = False
                    self.parser.running = False
                    break
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                    total_errors += len(batch_app_ids)
                    
                    # Mark batch as error
                    for app_id in batch_app_ids:
                        self.checkpoint_manager.mark_itad_error(app_id, f"Batch processing error: {str(e)}")
                    
                    # Save checkpoint even on error
                    self.checkpoint_manager.save_checkpoint()
                    
                    # Continue with next batch instead of stopping
                    logger.info(f"Continuing with next batch after error in batch {batch_num}")
            
            # Final summary
            logger.info(f"\n{'='*70}")
            if not self.running:
                logger.info("PARSING STOPPED (not completed)")
            else:
                logger.info("PARSING COMPLETED")
            logger.info(f"{'='*70}")
            logger.info(f"Batches processed: {batches_completed}/{total_batches}")
            logger.info(f"Total apps processed successfully: {total_processed}")
            logger.info(f"Total apps with errors: {total_errors}")
            if batches_completed < total_batches:
                logger.info(f"Remaining batches: {total_batches - batches_completed}")
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


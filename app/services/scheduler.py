"""
Scheduler service for periodic tasks
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.survey_background_tasks import retry_failed_email_jobs, cleanup_old_survey_jobs

# Configure logging
logger = logging.getLogger(__name__)


class TaskScheduler:
    """Background task scheduler"""
    
    def __init__(self):
        self.is_running = False
        self.tasks = []
    
    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting task scheduler")
        
        # Create scheduled tasks
        retry_task = asyncio.create_task(self._schedule_retry_failed_emails())
        cleanup_task = asyncio.create_task(self._schedule_cleanup_old_jobs())
        
        self.tasks = [retry_task, cleanup_task]
        
        # Wait for tasks to complete (they run indefinitely)
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping task scheduler")
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to be cancelled
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks = []
    
    async def _schedule_retry_failed_emails(self):
        """Retry failed email jobs every 5 minutes"""
        while self.is_running:
            try:
                logger.debug("Checking for failed email jobs to retry")
                processed_count = await retry_failed_email_jobs(limit=50)
                if processed_count > 0:
                    logger.info(f"Processed {processed_count} failed email jobs")
            except Exception as e:
                logger.error(f"Error in retry failed emails task: {str(e)}")
            
            # Wait 5 minutes before next retry
            await asyncio.sleep(300)  # 5 minutes
    
    async def _schedule_cleanup_old_jobs(self):
        """Clean up old survey jobs every hour"""
        while self.is_running:
            try:
                logger.debug("Cleaning up old survey jobs")
                await cleanup_old_survey_jobs(days_old=30)
            except Exception as e:
                logger.error(f"Error in cleanup old jobs task: {str(e)}")
            
            # Wait 1 hour before next cleanup
            await asyncio.sleep(3600)  # 1 hour


# Global scheduler instance
scheduler = TaskScheduler()


async def start_scheduler():
    """Start the global scheduler"""
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler"""
    await scheduler.stop()
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from config.settings import settings
from utils.scraper import scrape_world_bank_literacy
from urllib.parse import urlparse

import logging
logger = logging.getLogger(__name__)

def start_scheduler():
    try:
        parsed = urlparse(settings.REDIS_URL)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        db = int(parsed.path.lstrip('/')) if parsed.path.lstrip('/') else 0

        jobstores = {
            'default': RedisJobStore(
                jobs_key='apscheduler.jobs', 
                run_times_key='apscheduler.run_times',
                host=host,
                port=port,
                db=db
            )
        }
        
        scheduler = BackgroundScheduler(jobstores=jobstores)
        
        # Check if the job already exists
        job_id = 'scrape_world_bank_job'
        existing_job = scheduler.get_job(job_id)
        
        if not existing_job:
            print(f"[SCHEDULER] Adding scraping job to run every {settings.SCRAPE_INTERVAL_MINUTES} minutes.")
            scheduler.add_job(
                scrape_world_bank_literacy,
                'interval',
                minutes=settings.SCRAPE_INTERVAL_MINUTES,
                id=job_id,
                replace_existing=True
            )
        else:
            print(f"[SCHEDULER] Scraping job already exists. Ensuring interval is {settings.SCRAPE_INTERVAL_MINUTES} minutes.")
            scheduler.reschedule_job(
                job_id,
                trigger='interval',
                minutes=settings.SCRAPE_INTERVAL_MINUTES
            )

        scheduler.start()
        print("[SCHEDULER] Started background scheduler using Redis.")
        return scheduler
    except Exception as e:
        logger.error(f"Gagal menginisialisasi scheduler atau koneksi Redis gagal: {e}")
        print(f"[SCHEDULER] Error: {e}")
        return None

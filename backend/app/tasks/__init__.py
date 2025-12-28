from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import models


class JobRunner:
	"""Lightweight job runner stub for background refresh tasks."""

	def __init__(self, session: AsyncSession):
		self.session = session

	async def start_job(self, job_type: str) -> models.Job:
		job = models.Job(type=job_type, status="running", started_at=datetime.utcnow())
		self.session.add(job)
		await self.session.flush()
		return job

	async def finish_job(self, job: models.Job, status: str = "succeeded", logs: str | None = None) -> models.Job:
		job.status = status
		job.finished_at = datetime.utcnow()
		job.logs = logs
		await self.session.flush()
		return job

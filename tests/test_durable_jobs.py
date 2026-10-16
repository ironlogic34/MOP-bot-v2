"""Durable job outbox: claim, retry/backoff, terminal failure, crash recovery."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core.database import Database
from shared.helpers import durable_jobs as jobs

class DurableJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "j.db"))
        await self.storage.open()
        await jobs.initialize(self.storage)
        self.t0 = datetime.now(timezone.utc)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def job(self, job_id):
        return (await self.storage.rows("SELECT * FROM shared_jobs WHERE id=?", (job_id,)))[0]

    async def test_success_runs_once(self):
        calls = []
        async def ok(value): calls.append(value)
        job_id = await jobs.enqueue(self.storage, "ping", {"value": 7})
        self.assertEqual(await jobs.process_pending(self.storage, {"ping": ok}, now=self.t0), 1)
        self.assertEqual(await jobs.process_pending(self.storage, {"ping": ok}, now=self.t0), 0)
        self.assertEqual(calls, [7])
        self.assertEqual((await self.job(job_id))["state"], "done")

    async def test_failure_backs_off_then_becomes_terminal(self):
        async def boom(**_): raise RuntimeError("token=abc123secret failed")
        job_id = await jobs.enqueue(self.storage, "x", {})
        now = self.t0
        for attempt in range(1, jobs.MAX_ATTEMPTS + 1):
            await jobs.process_pending(self.storage, {"x": boom}, now=now)
            row = await self.job(job_id)
            self.assertEqual(row["attempts"], attempt)
            if attempt < jobs.MAX_ATTEMPTS:
                self.assertEqual(row["state"], "pending")
                # Not due again until the backoff has elapsed.
                self.assertEqual(await jobs.process_pending(self.storage, {"x": boom}, now=now), 0)
                self.assertEqual((await self.job(job_id))["attempts"], attempt)
                now = datetime.fromisoformat(row["run_after"]) + timedelta(seconds=1)
        row = await self.job(job_id)
        self.assertEqual(row["state"], "failed")
        self.assertNotIn("abc123secret", row["last_error"])
        # Failed jobs are never picked up again.
        async def ok(**_): raise AssertionError("must not run")
        await jobs.process_pending(self.storage, {"x": ok}, now=now + timedelta(days=1))

    async def test_retry_can_succeed(self):
        state = {"n": 0}
        async def flaky():
            state["n"] += 1
            if state["n"] == 1:
                raise RuntimeError("transient")
        job_id = await jobs.enqueue(self.storage, "f", {})
        await jobs.process_pending(self.storage, {"f": flaky}, now=self.t0)
        later = datetime.fromisoformat((await self.job(job_id))["run_after"]) + timedelta(seconds=1)
        self.assertEqual(await jobs.process_pending(self.storage, {"f": flaky}, now=later), 1)
        self.assertEqual((await self.job(job_id))["state"], "done")

    async def test_unhandled_events_do_not_block_others(self):
        calls = []
        async def ok(): calls.append(1)
        for _ in range(30):
            await jobs.enqueue(self.storage, "unhandled", {})
        await jobs.enqueue(self.storage, "mine", {})
        self.assertEqual(await jobs.process_pending(self.storage, {"mine": ok}, limit=5, now=self.t0), 1)
        left = await self.storage.rows("SELECT COUNT(*) AS n FROM shared_jobs WHERE event='unhandled' AND state='pending'")
        self.assertEqual(left[0]["n"], 30)

    async def test_claim_is_exclusive(self):
        job_id = await jobs.enqueue(self.storage, "c", {})
        self.assertTrue(await jobs._claim(self.storage, job_id, self.t0.isoformat()))
        self.assertFalse(await jobs._claim(self.storage, job_id, self.t0.isoformat()))

    async def test_crashed_running_jobs_are_requeued_on_initialize(self):
        job_id = await jobs.enqueue(self.storage, "c", {})
        await jobs._claim(self.storage, job_id, self.t0.isoformat())
        self.assertEqual((await self.job(job_id))["state"], "running")
        await jobs.initialize(self.storage)
        self.assertEqual((await self.job(job_id))["state"], "pending")

    async def test_payload_validation(self):
        with self.assertRaises(ValueError):
            await jobs.enqueue(self.storage, "x", ["not", "a", "dict"])
        with self.assertRaises(ValueError):
            await jobs.enqueue(self.storage, "x", {"big": "a" * 20000})
        with self.assertRaises(ValueError):
            await jobs.enqueue(self.storage, " ", {})

if __name__ == "__main__":
    unittest.main()

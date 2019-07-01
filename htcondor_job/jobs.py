# Copyright 2019 HTCondor Team, Computer Sciences Department,
# University of Wisconsin-Madison, WI.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import enum
import uuid
import time
from pathlib import Path
import threading
from copy import copy
import weakref

import htcondor

LOG_DIR = Path.home() / ".job_logs"
LOG_DIR.mkdir(parents = True, exist_ok = True)

JOBS = weakref.WeakSet()


def read_events():
    while True:
        time.sleep(.1)

        for job in copy(JOBS):
            for event in job._events:
                maybe_new_state = JOB_STATE_TRANSITIONS.get(event.type, None)
                if maybe_new_state is not None:
                    job._state = maybe_new_state


EVENT_THREAD = threading.Thread(
    target = read_events,
    daemon = True,
)
EVENT_THREAD.start()


class JobState(enum.Enum):
    Unsubmitted = enum.auto()
    Idle = enum.auto()
    Running = enum.auto()
    Submitted = enum.auto()
    Held = enum.auto()
    Completed = enum.auto()
    Removed = enum.auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


JOB_STATE_TRANSITIONS = {
    htcondor.JobEventType.SUBMIT: JobState.Idle,
    htcondor.JobEventType.JOB_EVICTED: JobState.Idle,
    htcondor.JobEventType.JOB_UNSUSPENDED: JobState.Idle,
    htcondor.JobEventType.JOB_RELEASED: JobState.Idle,
    htcondor.JobEventType.SHADOW_EXCEPTION: JobState.Idle,
    htcondor.JobEventType.JOB_RECONNECT_FAILED: JobState.Idle,
    htcondor.JobEventType.JOB_TERMINATED: JobState.Completed,
    htcondor.JobEventType.EXECUTE: JobState.Running,
    htcondor.JobEventType.JOB_HELD: JobState.Held,
    htcondor.JobEventType.JOB_ABORTED: JobState.Removed,
}


class Job:
    def __init__(
        self,
        executable,
        arguments = None,
        input_files = None,
        output_files = None,
    ):
        self.uid = uuid.uuid4()

        self._executable = executable
        self._arguments = arguments or []
        self._input_files = input_files or []
        self._output_files = output_files or []
        self._event_log_path = LOG_DIR / str(self.uid)
        self._event_log_path.touch(exist_ok = True)
        self._events = htcondor.JobEventLog(self._event_log_path.as_posix()).events(0)

        self._state = JobState.Unsubmitted
        self._jobid = None

        JOBS.add(self)

    def __str__(self):
        lines = [repr(self)]

        lines.extend(f"  {line}" for line in (
            f"executable = {self._executable}",
            f"arguments = {self._arguments}",
            f"input files = {self._input_files}",
            f"output files = {self._output_files}"
        ))

        return '\n'.join(lines)

    def __repr__(self):
        return f"Job {self.uid} [{self.state}]"

    def __del__(self):
        JOBS.remove(self)

    @property
    def state(self):
        return self._state

    def submit(self):
        sub = htcondor.Submit(dict(
            executable = self._executable,
            arguments = " ".join(self._arguments),
            transfer_input_files = ", ".join(self._input_files),
            transfer_output_files = ", ".join(self._output_files),
            log = self._event_log_path.as_posix(),
        ))

        schedd = htcondor.Schedd()
        with schedd.transaction() as txn:
            clusterid = sub.queue(txn, 1)

        self._jobid = (clusterid, 0)

        return self

    @property
    def _constraint(self):
        cluster, proc = self._jobid
        return f"(ClusterID == {cluster} && ProcID == {proc})"

    def hold(self):
        schedd = htcondor.Schedd()
        schedd.act(htcondor.JobAction.Hold, self._constraint)
        return self

    def release(self):
        schedd = htcondor.Schedd()
        schedd.act(htcondor.JobAction.Release, self._constraint)
        return self

    def remove(self):
        schedd = htcondor.Schedd()
        schedd.act(htcondor.JobAction.Remove, self._constraint)
        return self

    @property
    def output_files(self):
        yield from (Path(x) for x in self._output_files)


class Jobs:
    def __init__(self, jobs):
        self.jobs = list(jobs)

    def __iter__(self):
        yield from self.jobs

    @property
    def state(self):
        return [job.state for job in self]

    def submit(self):
        for job in self:
            job.submit()

    def hold(self):
        for job in self:
            job.hold()

    def release(self):
        for job in self:
            job.release()

    def remove(self):
        for job in self:
            job.remove()

    @property
    def output_files(self):
        yield from (job.output_files for job in self)

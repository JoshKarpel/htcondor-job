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

import cloudpickle

import htcondor

TASKS = weakref.WeakSet()


def read_events():
    while True:
        time.sleep(.1)

        for task in copy(TASKS):
            for event in task._events:
                maybe_new_state = TASK_STATE_TRANSITIONS.get(event.type, None)
                if maybe_new_state is not None:
                    task._state = maybe_new_state


EVENT_THREAD = threading.Thread(
    target = read_events,
    daemon = True,
)
EVENT_THREAD.start()


class TaskState(enum.Enum):
    Unsubmitted = enum.auto()
    Idle = enum.auto()
    Running = enum.auto()
    Submitted = enum.auto()
    Held = enum.auto()
    Completed = enum.auto()
    Removed = enum.auto()

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"


TASK_STATE_TRANSITIONS = {
    htcondor.JobEventType.SUBMIT: TaskState.Idle,
    htcondor.JobEventType.JOB_EVICTED: TaskState.Idle,
    htcondor.JobEventType.JOB_UNSUSPENDED: TaskState.Idle,
    htcondor.JobEventType.JOB_RELEASED: TaskState.Idle,
    htcondor.JobEventType.SHADOW_EXCEPTION: TaskState.Idle,
    htcondor.JobEventType.JOB_RECONNECT_FAILED: TaskState.Idle,
    htcondor.JobEventType.JOB_TERMINATED: TaskState.Completed,
    htcondor.JobEventType.EXECUTE: TaskState.Running,
    htcondor.JobEventType.JOB_HELD: TaskState.Held,
    htcondor.JobEventType.JOB_ABORTED: TaskState.Removed,
}


class Task:
    def __init__(
        self,
        function,
        input_file,
        working_dir = None
    ):
        self.function = function
        self.input_file = input_file

        if working_dir is None:
            working_dir = Path.cwd()

        self.uid = uuid.uuid4()

        self.working_dir = working_dir
        self.working_dir.mkdir(parents = True, exist_ok = True)
        self._event_log_path = self.working_dir / f'{self.uid}.log'
        self._event_log_path.touch(exist_ok = True)
        self._events = htcondor.JobEventLog(self._event_log_path.as_posix()).events(0)

        self._state = TaskState.Unsubmitted
        self._jobid = None

        TASKS.add(self)

    def __repr__(self):
        return f"Task {self.uid} [{self.state}]"

    def __del__(self):
        TASKS.remove(self)

    @property
    def state(self):
        return self._state

    def submit(self):
        func_path = self.working_dir / f'{self.uid}.func'
        with func_path.open(mode = 'wb') as f:
            cloudpickle.dump(self.function, f)

        sub = htcondor.Submit(dict(
            executable = str(Path(__file__).parent / 'run.py'),
            arguments = f'{self.uid} {self.input_file}',
            transfer_input_files = f'{self.input_file}, {func_path}',
            transfer_output_files = f'{self.uid}.output',
            output = str(self.working_dir / f'{self.uid}.out'),
            error = str(self.working_dir / f'{self.uid}.err'),
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

    def _act(self, action):
        schedd = htcondor.Schedd()
        schedd.act(action, self._constraint)
        return self

    def hold(self):
        return self._act(htcondor.JobAction.Hold)

    def release(self):
        return self._act(htcondor.JobAction.Release)

    def remove(self):
        return self._act(htcondor.JobAction.Remove)

    @property
    def output_file(self):
        if self.state is not TaskState.Completed:
            raise Exception('Task is not complete yet!')
        return self.working_dir / f'{self.uid}.output'

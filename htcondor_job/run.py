#!/usr/bin/env python3

# Copyright 2018 HTCondor Team, Computer Sciences Department,
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

import os
import shutil
import sys
import socket
import datetime
import gzip
import textwrap
import traceback
import subprocess
import getpass
from pathlib import Path

import cloudpickle


def main(uid, input_file):
    func_path = Path.cwd() / f'{uid}.func'
    with func_path.open(mode = 'rb') as f:
        func = cloudpickle.load(f)

    input_file_path = Path.cwd() / Path(input_file).name
    output_file_path = Path.cwd() / f'{uid}.output'

    func(input_file_path, output_file_path)


if __name__ == '__main__':
    main(uid = sys.argv[1], input_file = sys.argv[2])

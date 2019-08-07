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

import os
import re
from pathlib import Path

from setuptools import setup

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

setup(
    name = "htcondor-job",
    version = "0.0.1",
    author = "Josh Karpel",
    author_email = "josh.karpel@gmail.com",
    long_description = Path("README.md").read_text(),
    long_description_content_type = "text/markdown",
    packages = ["htcondor_job"],
    install_requires = Path("requirements.txt").read_text().splitlines(),
)

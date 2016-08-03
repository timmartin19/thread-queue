#!/usr/bin/env bash -evx

mkvirtualenv "thread-queue"
workon "thread-queue"

pip install -e .
pip install -r requirements_dev.txt

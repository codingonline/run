#!/usr/bin/env python
# encoding: utf-8

from controller import AutoScaler
from apscheduler.schedulers.blocking import BlockingScheduler

def test_as_findbugs():
    auto_scaler = AutoScaler(12)
    scheduler = BlockingScheduler()
    scheduler.add_job(auto_scaler.scale, 'interval', seconds=2)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    test_as_findbugs()

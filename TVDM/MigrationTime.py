'''
    Description:

'''
from __future__ import division

import datetime


def timedelta2microseconds(time):
    if not time:
        return -1
    return (((24 * 60 * 60 * time.days) + time.seconds)) * 10 ** 6 + time.microseconds


def time2microseconds(time):
    if not time:
        return -1
    return (((60 * time.hours) + time.minutes) * 60 + time.seconds) * 1000000 + time.microseconds


def microseconds2timedelta(pass_microseconds):
    given_microseconds = int(pass_microseconds)
    microseconds = given_microseconds % (10 ** 6)
    rest = int(given_microseconds / 10 ** 6)
    seconds = int(rest % (60 * 60 * 24))
    days = int(rest / (60 * 60 * 24))
    return datetime.timedelta(days=days, seconds=seconds, microseconds=microseconds)


def microseconds2time(given_microseconds):
    microseconds = given_microseconds % (10 ** 6)
    rest = int(given_microseconds / 10 ** 6)
    seconds = int(rest % 60)
    rest = int(rest / 60)
    minutes = int(rest % 60)
    rest = int(rest / 60)
    hours = int(rest % 60)
    return datetime.time(hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds)

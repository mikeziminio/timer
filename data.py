#!/usr/bin/python3.12

import functools
import sqlite3
import typing
from datetime import datetime, timedelta
import time
import zoneinfo

from settings import settings


def seconds_to_hms(sec: float | int) -> tuple:
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    seconds = int(sec % 60)
    return hours, minutes, seconds


class Period(typing.NamedTuple):
    time_start: float
    time_end: float
    hours: int
    minutes: int
    seconds: int
    comment: str
    pause_time: float

    def __repr__(self):

        local_zone = zoneinfo.ZoneInfo(settings['time_zone_name'])

        if self.time_start is None:
            datetime_start = '--:--:--'
        else:
            datetime_start = datetime.fromtimestamp(self.time_start, tz=local_zone).strftime('%d.%m.%Y %H:%M:%S')

        if self.time_end is None:
            datetime_end = '--:--:--'
        else:
            datetime_end = datetime.fromtimestamp(self.time_end, tz=local_zone).strftime('%H:%M:%S')

        if self.comment is None:
            comment = ''
        else:
            comment = self.comment

        if self.time_end is None:
            h, m, s = seconds_to_hms(time.time() - self.time_start - self.pause_time)
            duration = f'{h:02d}:{m:02d}:{s:02d}'
        else:
            duration = f'{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}'

        # if not self.pause_time:
        #     pause = ''
        # else:
        #     h, m, s = seconds_to_hms(self.pause_time)
        #     pause = f'pause {h:02d}:{m:02d}:{s:02d}'

        return f'{datetime_start}\t{datetime_end}\t{duration}\t{comment}'


class TimerDB:

    sqlite_db_path = settings['sqlite_db_path']

    @functools.cache
    def get_connection(self):
        connection = sqlite3.connect(self.sqlite_db_path)
        connection.autocommit = False
        return connection

    def start_new_period(self, comment: str = None):
        con = self.get_connection()
        con.execute('''
            INSERT INTO period(time_start, comment) VALUES
            (:time_start, :comment)
        ''', {
            'time_start': datetime.now().timestamp(),
            'comment': comment
        })
        con.commit()

    def get_current_period_pk(self) -> float | None:
        con = self.get_connection()

        current_period = con.execute('''
            SELECT time_start
            FROM period
            WHERE time_end IS NULL
        ''').fetchone()

        if current_period is not None:
            return current_period[0]

    def stop_current_period(self, comment: str = None):
        con = self.get_connection()

        # Если нет текущего периода, то остановка не требуется
        current_period_pk = self.get_current_period_pk()
        if current_period_pk is None:
            return

        pause_time, = con.execute('''
            SELECT pause_time
            FROM period
            WHERE time_start = :time_start
        ''', {
            'time_start': current_period_pk,
        }).fetchone()

        time_start = datetime.fromtimestamp(current_period_pk)
        time_end = datetime.now()
        delta = time_end - time_start
        hours, minutes, seconds = seconds_to_hms(delta.seconds - pause_time)

        if comment:
            con.execute('''
                UPDATE period SET comment = :comment
                WHERE time_start = :time_start
            ''', {
                'time_start': current_period_pk,
                'comment': comment,
            })
        con.execute('''
            UPDATE period SET
                time_end = :time_end,
                hours = :hours,
                minutes = :minutes,
                seconds = :seconds
            WHERE time_end IS NULL
        ''', {
            'time_end': time_end.timestamp(),
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
        })
        con.commit()

    def add_pause_time(self, pause_time: float):
        con = self.get_connection()

        # Если нет текущего периода, то обновить не можем
        current_period_pk = self.get_current_period_pk()
        if current_period_pk is None:
            return

        con.execute('''
            UPDATE period SET pause_time = pause_time + :pause_time
            WHERE time_start = :time_start
        ''', {
            'pause_time': pause_time,
            'time_start': current_period_pk
        })
        con.commit()

    def update_current_comment(self, comment: str):
        con = self.get_connection()

        # Если нет текущего периода, то обновить не можем
        current_period_pk = self.get_current_period_pk()
        if current_period_pk is None:
            return

        con.execute('''
            UPDATE period SET comment = :comment
            WHERE time_start = time_start
        ''', {
            'comment': comment,
            'time_start': current_period_pk
        })
        con.commit()

    def get_current_statistics(self):
        con = self.get_connection()

        current_period_pk = self.get_current_period_pk()
        if current_period_pk is None:
            return

        current_period = con.execute('''
            SELECT *
            FROM period
            WHERE time_start = :time_start
        ''', {
            'time_start': current_period_pk,
        }).fetchone()

        return Period._make(current_period)

    def get_periods(self, from_time: float = 0):

        con = self.get_connection()
        rows = con.execute('''
            SELECT * FROM period
            WHERE time_start >= :from_time
        ''', {
            'from_time': from_time
        }).fetchall()
        periods = (Period._make(row) for row in rows)

        return periods


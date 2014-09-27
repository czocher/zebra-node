# -*- coding: utf-8 -*-

from os import statvfs
from os.path import abspath


def get_free_memory():
    with open('/proc/meminfo', 'r') as mem:
        total, free, buffers, cached = [int(next(mem).split()[1])
                                        for x in xrange(4)]
    return free + cached


def get_processor_frequency():
    with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') \
            as cpu:
        frequency = int(cpu.read())
    return frequency


def get_free_diskspace():
    s = statvfs(abspath(__file__))

    # Number of free bytes that ordinary users are allowed to users
    free = s.f_frsize * s.f_bavail / 1000000
    return free

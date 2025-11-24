#!/usr/bin/env python3
"""
ems.py
  5) EMS  - EMS thread (every 1s) doing calculations
"""

import threading
import binascii
import socket
import csv
import time
import datetime
import random
import sys
import os
import globl

from typing import Optional
from datetime import datetime
from pymodbus.client import ModbusSerialClient

# -----------------------------------------------------------------
module_name = " EMS"
# -----------------------------------------------------------------

# -----------------------------------------------------------------------------------------
# --- EMS thread --------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------

def ems_thread_fn(ems_stop_event: threading.Event, interval: float = 2.0):
    cntr = 0
    while not ems_stop_event.is_set():
        cntr += 1
        time.sleep(interval)
        globl.log_debug(module_name, f"Loop counter {cntr}")

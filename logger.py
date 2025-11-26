#!/usr/bin/env python3
"""
logger.py
thread 4 writes log data to a csv file every 4 seconds and 
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
module_name = " LOG"
# -----------------------------------------------------------------

# -----------------------------------------------------------------------------------------
# --- LOGGER thread -----------------------------------------------------------------------
# -----------------------------------------------------------------------------------------
        
def logger_thread_fn(log_stop_event: threading.Event, interval: float = 1.0):
    cntr = 0
    while not log_stop_event.is_set():
        cntr += 1
        # updated in dsmr and made available via global variables in globl.py
        # - globl.power_cons 
        # - globl.power_prod 
        #globl.log_debug(module_name, f"globl.power_cons: {globl.power_cons} Watt")
        #globl.log_debug(module_name, f"globl.power_prod: {globl.power_prod} Watt")
        time.sleep(interval)
        globl.log_loop(module_name, f"Loop counter {cntr}")
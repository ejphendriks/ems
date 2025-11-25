#!/usr/bin/env python3
"""
bsld.py
  3) BSLD - Baseload reader (every 10s) checking for changes in base load file
  start bsld    - start ems thread
  stop bsld     - stop ems thread
thread 3 reads the Baseload csv file every 10 seconds and checks if the the base load data has changed, 
The DSMR and MODBUS data should be shared as global data
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
module_name = "BSLD"
# -----------------------------------------------------------------
    
BASELOAD_CSV = "baseload.csv"
LOG_CSV = "logs.csv"

# -----------------------------------------------------------------------------------------
# --- BASELOAD thread ---------------------------------------------------------------------
# -----------------------------------------------------------------------------------------

def baseload_thread_fn(bsld_stop_event: threading.Event, interval: float = 1.0):
    cntr = 0
    while not bsld_stop_event.is_set():
        
        # Only execute every 10 times
        if ((cntr % 10) == 0): 

            # Path to your CSV file
            file_path = "baseload.csv"

            # Open the file manually
            csvfile = open(file_path, newline='', encoding='utf-8')

            # Create a CSV reader using ';' as delimiter
            reader = csv.reader(csvfile, delimiter=';')

            # store header in a list
            globl.baseload_header = next(reader)
            
            # --- Only print BSLD data if requested
            if globl.show_bsld:
                print(f"[BSLD] {globl.baseload_header[0]} \t\t {globl.baseload_header[1]} \t {globl.baseload_header[2]} \t {globl.baseload_header[3]} \t {globl.baseload_header[4]}")

            # Read all rows into a list
            rows = list(reader)

            # extracting each data row one by one
            try:
                for row in rows:
                    globl.baseload_data.append(row)
                    ihour = int(row[0])
                    bena = bool(row[1])
                    bpvz = bool(row[2])
                    bnom = bool(row[3])
                    ipwr = int(row[4])
                    if globl.show_bsld:
                        print(f"[BSLD] HOUR:{ihour}   \t {bena} \t {bpvz} \t {bnom} \t POWER:{ipwr}")
                    
            except:
                globl.log_debug(module_name, f"baseload.csv could not be read or is corrupt...\n")

            # Close the file manually
            csvfile.close()

        cntr += 1
        globl.log_debug(module_name, f"Loop counter {cntr}")
        time.sleep(interval)
        

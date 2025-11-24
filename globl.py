#!/usr/bin/env python3
"""
globl.py
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

from typing import Optional
from datetime import datetime
from pymodbus.client import ModbusSerialClient

# -----------------------------------------------------------------------------
# ---- Global flags for triggering events and logging -------------------------
# -----------------------------------------------------------------------------

show_dsmr = False
show_batt = False
show_bsld = False

show_debug = True

# -----------------------------------------------------------------------------
# ---- Global thread control --------------------------------------------------
# -----------------------------------------------------------------------------

threads = {}    # --- list of threads 

# --- Stop events  

batt_stop_event = threading.Event()     # baseload stop signal
dsmr_stop_event  = threading.Event()    # baseload stop signal
bsld_stop_event = threading.Event()     # baseload stop signal
log_stop_event = threading.Event()      # logger stop signal
ems_stop_event = threading.Event()      # ems stop signal

# --- Shared global data (protected by locks) 

batt_lock = threading.Lock()
dsmr_lock = threading.Lock()
bsld_lock = threading.Lock()
log_lock = threading.Lock()
ems_lock = threading.Lock()



# -----------------------------------------------------------------------------
# ---- Utilities --------------------------------------------------------------
# -----------------------------------------------------------------------------


# --- create log sentence
def log_debug(module, sentence):
    if show_debug:
        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] [{module}] - {sentence}")

# -----------------------------------------------------------------------------
# --- BATT global constants and variables ---------------------------------------------------------
# -----------------------------------------------------------------------------

batt_data = []          # Global list with converted BATT MODBUS values

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# --- DSMR DATA FIELD ---------------------------------------------------------
# -----------------------------------------------------------------------------

DSMR_VERSION        =  0 # --- 0.2.8    --- DSMR version number
DSMR_TIME_STAMP     =  1 # --- 1.0.0    --- Time stamp (251022130635S)
DSMR_SERIAL_NUM     =  2 # --- 96.1.1   --- Serial Number 
DSMR_ENRG_T1_CONS   =  3 # --- 1.8.1    --- Electricity consumed by client (Tariff 1) in 0,001 kWh
DSMR_ENRG_T2_CONS   =  4 # --- 1.8.2    --- Electricity consumed by client (Tariff 2) in 0,001 kWh
DSMR_ENRG_T1_PROD   =  5 # --- 2.8.1    --- Electricity produced by client (Tariff 1) in 0,001 kWh
DSMR_ENRG_T2_PROD   =  6 # --- 2.8.2    --- Electricity produced by client (Tariff 2) in 0,001 kWh
DSMR_ACTIVE_TARIF   =  7 # --- 96.14.0  --- Active tarif
DSMR_PWR_TOT_CONS   =  8 # --- 1.7.0    --- Actual electricity power delivered (+P) in Watt 
DSMR_PWR_TOT_PROD   =  9 # --- 2.7.0    --- Actual electricity power received (-P) in Watt
DSMR_VOLT_L1        = 10 # --- 32.7.0   --- Instantaneous voltage L1 1-0:32.7.0.255
DSMR_VOLT_L2        = 11 # --- 52.7.0   --- Instantaneous voltage L2 1-0:52.7.0.255
DSMR_VOLT_L3        = 12 # --- 72.7.0   --- Instantaneous voltage L3 1-0:72.7.0.255
DSMR_CURR_L1        = 13 # --- 31.7.0   --- Instantaneous current L1 1-0:31.7.0.255
DSMR_CURR_L2        = 14 # --- 51.7.0   --- Instantaneous current L2 1-0:51.7.0.255
DSMR_CURR_L3        = 15 # --- 71.7.0   --- Instantaneous current L3 1-0:71.7.0.255
DSMR_PWR_L1_CONS    = 16 # --- 21.7.0   --- Instantaneous active power L1 (+P) 1-0:21.7.0.255
DSMR_PWR_L2_CONS    = 17 # --- 41.7.0   --- Instantaneous active power L2 (+P) 1-0:41.7.0.255
DSMR_PWR_L3_CONS    = 18 # --- 61.7.0   --- Instantaneous active power L3 (+P) 1-0:61.7.0.255
DSMR_PWR_L1_PROD    = 19 # --- 22.7.0   --- Instantaneous active power L1 (-P) 1-0:22.7.0.255
DSMR_PWR_L2_PROD    = 20 # --- 42.7.0   --- Instantaneous active power L2 (-P) 1-0:42.7.0.255
DSMR_PWR_L3_PROD    = 21 # --- 62.7.0   --- Instantaneous active power L3 (-P)
DSMR_GAS_SERIAL_NUM = 22 # --- 96.1.0   --- Serial Number 
DSMR_GAS_TIME_STAMP = 23 # --- 24.2.1   --- Gas timestamp
DSMR_GAS_VOLUME     = 24 # --- 24.2.1   --- Gas in m3

# --- OBIS LIST --------------------------------------------------------------------------

OBIS_LIST = [
"1.0.0",
"0.2.8",
"96.1.1",
"1.8.1",
"1.8.2",
"2.8.1",
"2.8.2",
"96.14.0",
"1.7.0",
"2.7.0",
"32.7.0",
"52.7.0",
"72.7.0",
"31.7.0",
"51.7.0",
"71.7.0",
"21.7.0",
"41.7.0",
"61.7.0",
"22.7.0",
"42.7.0",
"62.7.0",
"96.1.0",
"24.2.1",
"24.2.1"
]

# --- DSMR OBIS DATA LIST --------------------------------------------------------------------------

# --- Index for DSMR fields ----
IDXD_NAME = 0   # - Field name 
IDXD_OBIS = 1   # - OBIS identifier
IDXD_TYPE = 2   # - Type of value
IDXD_SVAL = 3   # - Raw string value
IDXD_NVAL = 4   # - Nummeric value    
IDXD_DIVR = 5   # - Divider (/1000)
IDXD_UNIT = 6   # - Unit (kWh)

# --- supporting variables
str_value = "mtr-value"
num_value = 0

DSMR_OBIS_LIST = [
["DSMR_VERSION", "0.2.8", "u", str_value, num_value, 10, ""],
["DSMR_TIME_STAMP", "1.0.0", "t", str_value, num_value, 1, ""],
["DSMR_SERIAL_NUM", "96.1.1", "s", str_value, num_value, 1, ""],
["DSMR_ENRG_T1_CONS", "1.8.1", "u", str_value, num_value, 1000, "Wh"],
["DSMR_ENRG_T2_CONS", "1.8.2", "u", str_value, num_value, 1000, "Wh"],
["DSMR_ENRG_T1_PROD", "2.8.1", "u", str_value, num_value, 1000, "Wh"],
["DSMR_ENRG_T2_PROD", "2.8.2", "u", str_value, num_value, 1000, "Wh"],
["DSMR_ACTIVE_TARIF", "96.14.0", "u", str_value, num_value, 1, ""],
["DSMR_PWR_TOT_CONS", "1.7.0", "u", str_value, num_value, 1, "W CONS"],
["DSMR_PWR_TOT_PROD", "2.7.0", "u", str_value, num_value, 1, "W PROD"],
["DSMR_VOLT_L1", "32.7.0", "u", str_value, num_value, 10, "V L1"],
["DSMR_VOLT_L2", "52.7.0", "u", str_value, num_value, 10, "V L2"],
["DSMR_VOLT_L3", "72.7.0", "u", str_value, num_value, 10, "V L3"],
["DSMR_CURR_L1", "31.7.0", "u", str_value, num_value, 1, "A L1"],
["DSMR_CURR_L2", "51.7.0", "u", str_value, num_value, 1, "A L2"],
["DSMR_CURR_L3", "71.7.0", "u", str_value, num_value, 1, "A L3"],
["DSMR_PWR_L1_CONS", "21.7.0", "u", str_value, num_value, 1, "W L1 CONS"],
["DSMR_PWR_L2_CONS", "41.7.0", "u", str_value, num_value, 1, "W L2 CONS"],
["DSMR_PWR_L3_CONS", "61.7.0", "u", str_value, num_value, 1, "W L3 CONS"],
["DSMR_PWR_L1_PROD", "22.7.0", "u", str_value, num_value, 1, "W L1 PROD"],
["DSMR_PWR_L2_PROD", "42.7.0", "u", str_value, num_value, 1, "W L2 PROD"],
["DSMR_PWR_L3_PROD", "62.7.0", "u", str_value, num_value, 1, "W L3 PROD"],
["DSMR_GAS_SERIAL_NUM", "96.1.0", "s", str_value, num_value, 1, ""],
["DSMR_GAS_TIME_STAMP", "24.2.1", "t", str_value, num_value, 1, ""],
["DSMR_GAS_VOLUME", "24.2.1", "u", str_value, num_value, 1000, "m3"]
]

# -----------------------------------------------------------------------------
# --- BASELOAD global constants and variables ---------------------------------------------------------
# -----------------------------------------------------------------------------

# initializing the header and data list for baseload
baseload_header = []
baseload_data = []

# -----------------------------------------------------------------------------

#ems_state = []          # latest EMS calculations / results

# -----------------------------------------------------------------------------

power_cons = 0          # global power consumed
power_prod = 0          # global power produced

# -----------------------------------------------------------------------------

str_telegram = "/ISK5\2M550T-1012"  # hold the incoming p1 telegram as a string

# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# --- CONST declarations ------------------------------------------------------
# -----------------------------------------------------------------------------

#MODBUS_DEVICE = "/dev/ttyUSB0"
#MODBUS_BAUD = 115200
    
#DSMR_HOST = "192.168.101.182"
#DSMR_PORT = 23
    
#BASELOAD_CSV = "baseload.csv"
#LOG_CSV = "log.csv"



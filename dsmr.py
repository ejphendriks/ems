#!/usr/bin/env python3
"""
dsmr.py
  2) DSMR - Dutch Smart Meter client connects to port 23 reading DSMR P1 data
thread 2 is a TCP client that connects to a server on port 23 and received DSMR P1 data and 
The DSMR and MODBUS data will be shared as global data
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
module_name = "DSMR"
# -----------------------------------------------------------------

    
DSMR_HOST = "192.168.101.182"
DSMR_PORT = 23

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

# -----------------------------------------------------------------------------------------
# --- DSMR thread -------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------

def lookup_dsmr_value(telegram):
    
    for item in range(len(DSMR_OBIS_LIST)-1):   # Calculate DSMR_GAS_VOLUME separately (-1)
        indx_obis = telegram.find(DSMR_OBIS_LIST[item][IDXD_OBIS])
        indx_open_bracket = telegram[indx_obis:].find("(") + indx_obis + 1
        indx_close_bracket = telegram[indx_open_bracket:].find(")") + indx_open_bracket
        DSMR_OBIS_LIST[item][IDXD_SVAL] = telegram[indx_open_bracket:indx_close_bracket]
    
        if (DSMR_OBIS_LIST[item][IDXD_TYPE] == "u"): # if unsigned int --> number
            DSMR_OBIS_LIST[item][IDXD_NVAL] = int(''.join(filter(str.isdigit, DSMR_OBIS_LIST[item][IDXD_SVAL]))) / DSMR_OBIS_LIST[item][IDXD_DIVR]
            # --- Print incl the nummeric value and units
            if (len(DSMR_OBIS_LIST[item][IDXD_NAME]) >= 17): # only for outlining and formatting 
                if globl.show_dsmr: print(f"[DSMR] {DSMR_OBIS_LIST[item][IDXD_NAME]}\t{DSMR_OBIS_LIST[item][IDXD_OBIS]} \t = {DSMR_OBIS_LIST[item][IDXD_SVAL]} \t = {DSMR_OBIS_LIST[item][IDXD_NVAL]} {DSMR_OBIS_LIST[item][IDXD_UNIT]}")
            else:
                if globl.show_dsmr: print(f"[DSMR] {DSMR_OBIS_LIST[item][IDXD_NAME]}\t\t{DSMR_OBIS_LIST[item][IDXD_OBIS]} \t = {DSMR_OBIS_LIST[item][IDXD_SVAL]} \t = {DSMR_OBIS_LIST[item][IDXD_NVAL]} {DSMR_OBIS_LIST[item][IDXD_UNIT]}")
        else: # No need to print the nummeric value and unit because string or timestamp
            if (len(DSMR_OBIS_LIST[item][IDXD_NAME]) >= 17): # only for outlining and formatting 
                if globl.show_dsmr: print(f"[DSMR] {DSMR_OBIS_LIST[item][IDXD_NAME]}\t{DSMR_OBIS_LIST[item][IDXD_OBIS]} \t = {DSMR_OBIS_LIST[item][IDXD_SVAL]}")
            else:
                if globl.show_dsmr: print(f"[DSMR] {DSMR_OBIS_LIST[item][IDXD_NAME]}\t\t{DSMR_OBIS_LIST[item][IDXD_OBIS]} \t = {DSMR_OBIS_LIST[item][IDXD_SVAL]}")

    # --- Calculate DSMR_GAS_VOLUME separately (+1)
    indx_open_bracket = telegram[indx_close_bracket:].find("(") + indx_close_bracket + 1 # --- find next opening bracket
    indx_close_bracket = telegram[indx_open_bracket:].find(")") + indx_open_bracket      # --- find next closing bracket  
    item += 1 # this applies to the next row: DSMR_GAS_VOLUME
    DSMR_OBIS_LIST[item][IDXD_SVAL] = telegram[indx_open_bracket:indx_close_bracket - 1] # The -1 is needed to remove the extra 3 from "m3"
    DSMR_OBIS_LIST[item][IDXD_NVAL] = int(''.join(filter(str.isdigit, DSMR_OBIS_LIST[item][IDXD_SVAL]))) / DSMR_OBIS_LIST[item][IDXD_DIVR]

    # --- Only print DSMR data if requested
    if globl.show_dsmr: print(f"[DSMR] {DSMR_OBIS_LIST[item][IDXD_NAME]}\t\t{DSMR_OBIS_LIST[item][IDXD_OBIS]} \t = {DSMR_OBIS_LIST[item][IDXD_SVAL]} \t = {DSMR_OBIS_LIST[item][IDXD_NVAL]} {DSMR_OBIS_LIST[item][IDXD_UNIT]}")


def dsmr_thread_fn(dsmr_stop_event: threading.Event, interval: float = 2.0):

    cntr = 0
    host = "192.168.101.182"
    port = 23
    p1_counter = 0
    
    while not dsmr_stop_event.is_set():
        try:
            globl.log_debug(module_name, f"Connecting to Telnet server {host}:{port}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            client.settimeout(10)  # connection timeout
            globl.log_debug(module_name, f"Connected to {host}:{port}")
            client.settimeout(3)  # read timeout
            
            while not dsmr_stop_event.is_set():
                data = client.recv(1024)
                if not data:
                    globl.log_debug(module_name, f"Connection closed by server {host}:{port}")
                    break
                telegram = data.decode(errors='ignore')
                if len(telegram) > 800:  # --- Only analyse p1 telegram if complete (>800char)
                    lookup_dsmr_value(telegram)
                    # make available in ems thread via global variables
                    globl.power_cons = DSMR_OBIS_LIST[DSMR_PWR_TOT_CONS][IDXD_NVAL]
                    globl.power_prod = DSMR_OBIS_LIST[DSMR_PWR_TOT_PROD][IDXD_NVAL]

                    # calculate het voortschrijdend gemiddelde
                    #int_pwr_cons[0-9] = ++ ... / 10 etc
                    
        except Exception as e:
            globl.log_debug(module_name, f"Exception error: {e}")
            globl.log_debug(module_name, "Reconnecting in 5 seconds...")
            time.sleep(5)
        finally:
            try:
                client.close()
            except:
                pass

        cntr += 1
        globl.log_debug(module_name, f"Loop counter: {cntr}")

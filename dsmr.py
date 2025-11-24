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

# -----------------------------------------------------------------------------------------
# --- DSMR thread -------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------

def lookup_dsmr_value(telegram):
    
    for item in range(len(globl.DSMR_OBIS_LIST)-1):   # Calculate DSMR_GAS_VOLUME separately (-1)
        indx_obis = telegram.find(globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS])
        indx_open_bracket = telegram[indx_obis:].find("(") + indx_obis + 1
        indx_close_bracket = telegram[indx_open_bracket:].find(")") + indx_open_bracket
        globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL] = telegram[indx_open_bracket:indx_close_bracket]
    
        if (globl.DSMR_OBIS_LIST[item][globl.IDXD_TYPE] == "u"): # if unsigned int --> number
            globl.DSMR_OBIS_LIST[item][globl.IDXD_NVAL] = int(''.join(filter(str.isdigit, globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]))) / globl.DSMR_OBIS_LIST[item][globl.IDXD_DIVR]
            # --- Print incl the nummeric value and units
            if (len(globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]) >= 17): # only for outlining and formatting 
                if globl.show_dsmr: print(f"[DSMR] {globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]}\t{globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_NVAL]} {globl.DSMR_OBIS_LIST[item][globl.IDXD_UNIT]}")
            else:
                if globl.show_dsmr: print(f"[DSMR] {globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]}\t\t{globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_NVAL]} {globl.DSMR_OBIS_LIST[item][globl.IDXD_UNIT]}")
        else: # No need to print the nummeric value and unit because string or timestamp
            if (len(globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]) >= 17): # only for outlining and formatting 
                if globl.show_dsmr: print(f"[DSMR] {globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]}\t{globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]}")
            else:
                if globl.show_dsmr: print(f"[DSMR] {globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]}\t\t{globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]}")

    # --- Calculate DSMR_GAS_VOLUME separately (+1)
    indx_open_bracket = telegram[indx_close_bracket:].find("(") + indx_close_bracket + 1 # --- find next opening bracket
    indx_close_bracket = telegram[indx_open_bracket:].find(")") + indx_open_bracket      # --- find next closing bracket  
    item += 1 # this applies to the next row: DSMR_GAS_VOLUME
    globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL] = telegram[indx_open_bracket:indx_close_bracket - 1] # The -1 is needed to remove the extra 3 from "m3"
    globl.DSMR_OBIS_LIST[item][globl.IDXD_NVAL] = int(''.join(filter(str.isdigit, globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]))) / globl.DSMR_OBIS_LIST[item][globl.IDXD_DIVR]

    # --- Only print DSMR data if requested
    if globl.show_dsmr: print(f"[DSMR] {globl.DSMR_OBIS_LIST[item][globl.IDXD_NAME]}\t\t{globl.DSMR_OBIS_LIST[item][globl.IDXD_OBIS]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_SVAL]} \t = {globl.DSMR_OBIS_LIST[item][globl.IDXD_NVAL]} {globl.DSMR_OBIS_LIST[item][globl.IDXD_UNIT]}")


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
                    globl.power_cons = globl.DSMR_OBIS_LIST[globl.DSMR_PWR_TOT_CONS][globl.IDXD_NVAL]
                    globl.power_prod = globl.DSMR_OBIS_LIST[globl.DSMR_PWR_TOT_PROD][globl.IDXD_NVAL]

                    #if (globl.p1_interval > 0) and (globl.p1_interval == p1_counter):
                    #    print(f"[DSMR]:{telegram}")
                    #    p1_counter = 0
                    # increment p1_counter every second
                    #p1_counter += p1_counter

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

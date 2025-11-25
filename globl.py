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

show_debug = False

# -----------------------------------------------------------------------------
# ---- BATT fields taking values from MRST ------------------------------------
# -----------------------------------------------------------------------------

# --- BATT_INDEX_LIST is not starting with zero because of header in BATT_REG_LST
BATT_DEVICE_NAME = 1 #  31000 char n.a. 
BATT_FW_VERSION = 2 #  31100 u16 0.01 
BATT_SERIAL_NUM = 3 #  31200 char n.a. 
BATT_DC_VOLT = 4 #  32100 u16 0.01V 
BATT_DC_CURR = 5 #  32101 s16 0.01A 
BATT_DC_PWR_DIR = 6 #  32103 s32  positive means power into batt (charging)
BATT_DC_PWR_VAL = 7 #  32103 s32 1W positive means power into batt (charging)
BATT_DC_SOC = 8 #  32104 u16 0.1% 
BATT_DC_TOT_ENRG = 9 #  32105 u16 1wh 
BATT_AC_VOLT = 10 #  32200 u16 0.1V 
BATT_AC_CURR = 11 #  32201 s16 0.01A 
BATT_AC_PWR_DIR = 12 #  32202 s32  positive means power into the home (discharging)
BATT_AC_PWR_VAL = 13 #  32202 s32 1W positive means power into the home (discharging)
BATT_AC_FREQ = 14 #  32204 u16 0.01Hz 
BATT_BACKUP_VOLT = 15 #  32300 u16 0.1V 
BATT_BACKUP_CURR = 16 #  32301 u16 0.01A 
BATT_BACKUP_PWR_DIR = 17 #  32302 s32 1W 
BATT_BACKUP_PWR_VAL = 18 #  32302 s32 1W 
BATT_TOT_CHARGED = 19 #  33000 u32 0.01kWh 
BATT_TOT_DISCHARGED = 20 #  33002 u32 0.01kWh 
BATT_DAY_CHARGED = 21 #  33004 u32 0.01kWh 
BATT_DAY_DISCHARGED = 22 #  33006 u32 0.01kWh 
BATT_MNT_CHARGED = 23 #  33008 u32 0.01kWh 
BATT_MNT_DISCHARGED = 24 #  33010 u32 0.01kWh 
BATT_INT_TEMP = 25 #  35000 u16 0.1C 
BATT_MOS1_TEMP = 26 #  35001 u16 0.1C 
BATT_MOS2_TEMP = 27 #  35002 u16 0.1C 
BATT_MAX_CELL_TEMP = 28 #  35010 u16 0.1C 
BATT_MIN_CELL_TEMP = 29 #  35011 u16 0.1C 
BATT_INV_STATE = 30 #  35100 u16 n.a. 0:sleep, 1:standby, 2:charging, 3:discharging, 4:backup, 5:upgrading
BATT_LIMIT_VOLT = 31 #  35110 u16 100mv 
BATT_LIMIT_CHARGE_CURR = 32 #  35111 u16 100ma 
BATT_LIMIT_DISCHARG_CURR = 33 #  35112 u16 100ma 
BATT_ALARM = 34 #  36000 bits n.a. Alarm register
BATT_FAULT_LSB = 35 #  36100 bits n.a. Fault register
BATT_FAULT_MSB = 36 #  36100 bits n.a. Fault register
BATT_RESTART = 37 #  41000 u16 n.a. restart write 0x55AA 
BATT_UNIT_ID = 38 #  41100 u16 n.a. Set the Unit ID / Device ID
BATT_BACKUP = 39 #  41200 u16 n.a. 0: enable backup, 1: disable backup
BATT_RTU_MODE = 40 #  42000 u16 n.a. enable RS485 mode 0x55AA, disable: 0x55BB
BATT_INV_STATE = 41 #  42010 u16 n.a. 0:stop, 1:charge, 2:discharge
BATT_CHARGE_TO_SOC = 42 #  42011 u16 0,01 set charge to SoC value in 1%
BATT_PWR_CHARGE = 43 #  42020 u16 1W set charging power [0-2500W]
BATT_PWR_DISCHARGE = 44 #  42021 u16 1W set discharging power [0-2500W]
BATT_USER_MODE = 45 #  43000 u16 n.a. 0:manual, 1:anti-feed, 2:trade mode
BATT_CHARGE_CUTOFF = 46 #  44000 u16 0.1% 
BATT_DISCHARGE_CUTOFF = 47 #  44001 u16 0.1% 
BATT_MAX_CHARGE_PWR = 48 #  44002 u16 1W 
BATT_MAX_DISCHARGE_PWR = 49 #  44003 u16 1W 

cvalue = 0

BATT_REGISTER_LIST = [
["INDX","NAME","ABBR","CONV","UNIT","DESC"],
[1,"BATT_DEVICE_NAME","DN",cvalue," ",""],
[2,"BATT_FW_VERSION","FW",cvalue," ",""],
[3,"BATT_SERIAL_NUM","SN",cvalue," ",""],
[4,"BATT_DC_VOLT","DC",cvalue,"V",""],
[5,"BATT_DC_CURR","DC",cvalue,"A",""],
[6,"BATT_DC_PWR_DIR","DC",cvalue,"W","pos is charge"],
[7,"BATT_DC_PWR_VAL","DC",cvalue,"W","pos is charge"],
[8,"BATT_DC_SOC","DC",cvalue,"%",""],
[9,"BATT_DC_TOT_ENRG","DC",cvalue,"kWh",""],
[10,"BATT_AC_VOLT","AC",cvalue,"V",""],
[11,"BATT_AC_CURR","AC",cvalue,"A",""],
[12,"BATT_AC_PWR_DIR","AC",cvalue,"W","pos is discharge"],
[13,"BATT_AC_PWR_VAL","AC",cvalue,"W","pos is discharge"],
[14,"BATT_AC_FREQ","AC",cvalue,"Hz",""],
[15,"BATT_BACKUP_VOLT","BU",cvalue,"V",""],
[16,"BATT_BACKUP_CURR","BU",cvalue,"A",""],
[17,"BATT_BACKUP_PWR_DIR","BU",cvalue,"W","pos is discharge"],
[18,"BATT_BACKUP_PWR_VAL","BU",cvalue,"W","pos is discharge"],
[19,"BATT_TOT_CHARGED","ST",cvalue,"kWh",""],
[20,"BATT_TOT_DISCHARGED","ST",cvalue,"kWh",""],
[21,"BATT_DAY_CHARGED","ST",cvalue,"kWh",""],
[22,"BATT_DAY_DISCHARGED","ST",cvalue,"kWh",""],
[23,"BATT_MNT_CHARGED","ST",cvalue,"kWh",""],
[24,"BATT_MNT_DISCHARGED","ST",cvalue,"kWh",""],
[25,"BATT_INT_TEMP","TP",cvalue,"°C",""],
[26,"BATT_MOS1_TEMP","TP",cvalue,"°C",""],
[27,"BATT_MOS2_TEMP","TP",cvalue,"°C",""],
[28,"BATT_MAX_CELL_TEMP","CT",cvalue,"°C",""],
[29,"BATT_MIN_CELL_TEMP","CT",cvalue,"°C",""],
[30,"BATT_INV_STATE","IS",cvalue," ",""],
[31,"BATT_LIMIT_VOLT","LT",cvalue,"mv",""],
[32,"BATT_LIMIT_CHARGE_CURR","LT",cvalue,"ma",""],
[33,"BATT_LIMIT_DISCHARG_CURR","LT",cvalue,"ma",""],
[34,"BATT_ALARM","AL",cvalue," ","Alarm register"],
[35,"BATT_FAULT_LSB","FT",cvalue," ","Fault double register"],
[36,"BATT_FAULT_MSB","FT",cvalue," ","Fault double register"],
[37,"BATT_RESTART","RS",cvalue," ","0x55AA-->restart"],
[38,"BATT_UNIT_ID","UI",cvalue," ","unit id [1..255]"],
[39,"BATT_BACKUP","BK",cvalue," ","0:enable, 1:disbale"],
[40,"BATT_RTU_MODE","RM",cvalue," ","ON:0x55AA, OFF: 0x55BB"],
[41,"BATT_INV_STATE","IV",cvalue," ","0:stop,1:charge,2:discharge"],
[42,"BATT_CHARGE_TO_SOC","IV",cvalue," ","charge to target SOC"],
[43,"BATT_PWR_CHARGE","PW",cvalue,"W","range:[0..2500W]"],
[44,"BATT_PWR_DISCHARGE","PW",cvalue,"W","range:[0..2500W]"],
[45,"BATT_USER_MODE","UM",cvalue," ","0:manual,1:anti-feed,2:trade-mode"],
[46,"BATT_CHARGE_CUTOFF","CO",cvalue,"%","range:[80%..100%]"],
[47,"BATT_DISCHARGE_CUTOFF","CO",cvalue,"%","range:[12%..30%]"],
[48,"BATT_MAX_CHARGE_PWR","CO",cvalue,"W","range:[0..2500W]"],
[49,"BATT_MAX_DISCHARGE_PWR","CO",cvalue,"W","range:[0..2500W]"]
]

# --- BATT_FIELD_INDEX index for BATT fields ---- 
IDXB_INDX = 0   # - Index number
IDXB_NAME = 1   # - Field name 
IDXB_ABBR = 2   # - Abbreviation
IDXB_CONV = 3   # - Value
IDXB_UNIT = 4   # - Unit
IDXB_DESC = 5   # - Description


# -----------------------------------------------------------------------------
# ---- HOME fields taking values from DSMR ------------------------------------
# -----------------------------------------------------------------------------



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

# batt_data = []          # Global list with converted BATT MODBUS values

# -----------------------------------------------------------------------------


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



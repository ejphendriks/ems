#!/usr/bin/env python3
"""
batt.py

  1) BATT - Modbus RTU client over ttyUSB0 (uses pymodbus to communicate with the Marstek Venus E v2.0)
  start batt    - start ems thread
  stop batt     - stop ems thread
    thread 1 connects to a modbus master RTU over ttyUSB0, 
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
module_name = "MRST"
# -----------------------------------------------------------------

# -----------------------------------------------------------------
# --- Index MODBUS registers/groups for Marstek Venus E V20 -------
# -----------------------------------------------------------------

# --- not starting with zero because of the header
MRST_DEVICE_NAME = 1 #  31000 10 char n.a. 
MRST_FW_VERSION = 11 #  31100 1 u16 0.01 
MRST_SERIAL_NUM = 12 #  31200 10 char n.a. 
MRST_DC_VOLT = 22 #  32100 1 u16 0.01V 
MRST_DC_CURR = 23 #  32101 1 s16 0.01A 
MRST_DC_PWR_DIR = 24 #  32103 1 s32  positive means power into batt (charging)
MRST_DC_PWR_VAL = 25 #  32103 1 s32 1W positive means power into batt (charging)
MRST_DC_SOC = 26 #  32104 1 u16 0.1% 
MRST_DC_TOT_ENRG = 27 #  32105 1 u16 1wh 
MRST_AC_VOLT = 28 #  32200 1 u16 0.1V 
MRST_AC_CURR = 29 #  32201 1 s16 0.01A 
MRST_AC_PWR_DIR = 30 #  32202 1 s32  positive means power into the home (discharging)
MRST_AC_PWR_VAL = 31 #  32202 1 s32 1W positive means power into the home (discharging)
MRST_AC_FREQ = 32 #  32204 1 u16 0.01Hz 
MRST_BACKUP_VOLT = 33 #  32300 1 u16 0.1V 
MRST_BACKUP_CURR = 34 #  32301 1 u16 0.01A 
MRST_BACKUP_PWR_DIR = 35 #  32302 1 s32 1W 
MRST_BACKUP_PWR_VAL = 36 #  32302 1 s32 1W 
MRST_TOT_CHARGED = 37 #  33000 2 u32 0.01kWh 
MRST_TOT_DISCHARGED = 39 #  33002 2 u32 0.01kWh 
MRST_DAY_CHARGED = 41 #  33004 2 u32 0.01kWh 
MRST_DAY_DISCHARGED = 43 #  33006 2 u32 0.01kWh 
MRST_MNT_CHARGED = 45 #  33008 2 u32 0.01kWh 
MRST_MNT_DISCHARGED = 47 #  33010 2 u32 0.01kWh 
MRST_INT_TEMP = 49 #  35000 1 u16 0.1C 
MRST_MOS1_TEMP = 50 #  35001 1 u16 0.1C 
MRST_MOS2_TEMP = 51 #  35002 1 u16 0.1C 
MRST_MAX_CELL_TEMP = 52 #  35010 1 u16 0.1C 
MRST_MIN_CELL_TEMP = 53 #  35011 1 u16 0.1C 
MRST_INV_STATE = 54 #  35100 1 u16 n.a. 0:sleep, 1:standby, 2:charging, 3:discharging, 4:backup, 5:upgrading
MRST_LIMIT_VOLT = 55 #  35110 1 u16 100mv 
MRST_LIMIT_CHARGE_CURR = 56 #  35111 1 u16 100ma 
MRST_LIMIT_DISCHARG_CURR = 57 #  35112 1 u16 100ma 
MRST_ALARM = 58 #  36000 1 bits n.a. Alarm
MRST_FAULT_LSB = 59 #  36100 1bits n.a. Fault LSB
MRST_FAULT_MSB = 60 #  36101 12 bits n.a. Fault MSB
MRST_RESTART = 61 #  41000 1 u16 n.a. restart write 0x55AA 
MRST_UNIT_ID = 62 #  41100 1 u16 n.a. Set the Unit ID / Device ID
MRST_BACKUP = 63 #  41200 1 u16 n.a. 0: enable backup, 1: disable backup
MRST_RTU_MODE = 64 #  42000 1 u16 n.a. enable RS485 mode 0x55AA, disable: 0x55BB
MRST_INV_STATE = 65 #  42010 1 u16 n.a. 0:stop, 1:charge, 2:discharge
MRST_CHARGE_TO_SOC = 66 #  42011 1 u16 0,01 set charge to SoC value in 1%
MRST_PWR_CHARGE = 67 #  42020 1 u16 1W set charging power [0-2500W]
MRST_PWR_DISCHARGE = 68 #  42021 1 u16 1W set discharging power [0-2500W]
MRST_USER_MODE = 69 #  43000 1 u16 n.a. 0:manual, 1:anti-feed, 2:trade mode
MRST_CHARGE_CUTOFF = 70 #  44000 1 u16 0.1% 
MRST_DISCHARGE_CUTOFF = 71 #  44001 1 u16 0.1% 
MRST_MAX_CHARGE_PWR = 72 #  44002 1 u16 1W 
MRST_MAX_DISCHARGE_PWR = 73 #  44003 1 u16 1W 


# -----------------------------------------------------------------
# --- MARSTEK MODBUS REGISTERS --- Marstek Venus E V20 ------------------------ 
# -----------------------------------------------------------------

raw_value = 0
con_value = 0

MARSTEK_MODBUS = [
["INDX","NAME","ADDR","ABBR","BLCK","OFFSET","MODE","TYPE","RAWV","GAIN","CONV","UNIT","DESC"],
[1,"MRST_DEVICE_NAME",31000,"DN",10,0,"R","c",raw_value,1,con_value," ",""],
[2,"MRST_DEVICE_NAME",31001,"DN",0,1,"R","c",raw_value,1,con_value," ",""],
[3,"MRST_DEVICE_NAME",31002,"DN",0,2,"R","c",raw_value,1,con_value," ",""],
[4,"MRST_DEVICE_NAME",31003,"DN",0,3,"R","c",raw_value,1,con_value," ",""],
[5,"MRST_DEVICE_NAME",31004,"DN",0,4,"R","c",raw_value,1,con_value," ",""],
[6,"MRST_DEVICE_NAME",31005,"DN",0,5,"R","c",raw_value,1,con_value," ",""],
[7,"MRST_DEVICE_NAME",31006,"DN",0,6,"R","c",raw_value,1,con_value," ",""],
[8,"MRST_DEVICE_NAME",31007,"DN",0,7,"R","c",raw_value,1,con_value," ",""],
[9,"MRST_DEVICE_NAME",31008,"DN",0,8,"R","c",raw_value,1,con_value," ",""],
[10,"MRST_DEVICE_NAME",31009,"DN",0,9,"R","c",raw_value,1,con_value," ",""],
[11,"MRST_FW_VERSION",31100,"FW",1,0,"R","u",raw_value,0.01,con_value," ",""],
[12,"MRST_SERIAL_NUM",31200,"SN",10,0,"R","c",raw_value,1,con_value," ",""],
[13,"MRST_SERIAL_NUM",31201,"SN",0,1,"R","c",raw_value,1,con_value," ",""],
[14,"MRST_SERIAL_NUM",31202,"SN",0,2,"R","c",raw_value,1,con_value," ",""],
[15,"MRST_SERIAL_NUM",31203,"SN",0,3,"R","c",raw_value,1,con_value," ",""],
[16,"MRST_SERIAL_NUM",31204,"SN",0,4,"R","c",raw_value,1,con_value," ",""],
[17,"MRST_SERIAL_NUM",31205,"SN",0,5,"R","c",raw_value,1,con_value," ",""],
[18,"MRST_SERIAL_NUM",31206,"SN",0,6,"R","c",raw_value,1,con_value," ",""],
[19,"MRST_SERIAL_NUM",31207,"SN",0,7,"R","c",raw_value,1,con_value," ",""],
[20,"MRST_SERIAL_NUM",31208,"SN",0,8,"R","c",raw_value,1,con_value," ",""],
[21,"MRST_SERIAL_NUM",31209,"SN",0,9,"R","c",raw_value,1,con_value," ",""],
[22,"MRST_DC_VOLT",32100,"DC",6,0,"R","u",raw_value,0.01,con_value,"V",""],
[23,"MRST_DC_CURR",32101,"DC",0,1,"R","s",raw_value,0.01,con_value,"A",""],
[24,"MRST_DC_PWR_DIR",32102,"DC",0,2,"R","s",raw_value,1,con_value,"-->","pos is charge"],
[25,"MRST_DC_PWR_VAL",32103,"DC",0,3,"R","s",raw_value,1,con_value,"W","pos is charge"],
[26,"MRST_DC_SOC",32104,"DC",0,4,"R","u",raw_value,1,con_value,"%",""],
[27,"MRST_DC_TOT_ENRG",32105,"DC",0,5,"R","u",raw_value,0.01,con_value,"kWh",""],
[28,"MRST_AC_VOLT",32200,"AC",5,0,"R","u",raw_value,0.1,con_value,"V",""],
[29,"MRST_AC_CURR",32201,"AC",0,1,"R","u",raw_value,0.01,con_value,"A",""],
[30,"MRST_AC_PWR_DIR",32202,"AC",0,2,"R","s",raw_value,1,con_value,"-->","pos is discharge"],
[31,"MRST_AC_PWR_VAL",32203,"AC",0,3,"R","s",raw_value,1,con_value,"W","pos is discharge"],
[32,"MRST_AC_FREQ",32204,"AC",0,4,"R","u",raw_value,0.01,con_value,"Hz",""],
[33,"MRST_BACKUP_VOLT",32300,"BU",4,0,"R","u",raw_value,0.1,con_value,"V",""],
[34,"MRST_BACKUP_CURR",32301,"BU",0,1,"R","u",raw_value,0.01,con_value,"A",""],
[35,"MRST_BACKUP_PWR_DIR",32302,"BU",0,2,"R","s",raw_value,1,con_value,"W","pos is discharge"],
[36,"MRST_BACKUP_PWR_VAL",32303,"BU",0,3,"R","s",raw_value,1,con_value,"W","pos is discharge"],
[37,"MRST_TOT_CHARGED_H",33000,"ST",12,0,"R","u",raw_value,0.01,con_value,"kWh",""],
[38,"MRST_TOT_CHARGED_L",33001,"ST",0,1,"R","u",raw_value,0.01,con_value,"kWh",""],
[39,"MRST_TOT_DISCHARGED_H",33002,"ST",0,2,"R","u",raw_value,0.01,con_value,"kWh",""],
[40,"MRST_TOT_DISCHARGED_L",33003,"ST",0,3,"R","u",raw_value,0.01,con_value,"kWh",""],
[41,"MRST_DAY_CHARGED_H",33004,"ST",0,4,"R","u",raw_value,0.01,con_value,"kWh",""],
[42,"MRST_DAY_CHARGED_L",33005,"ST",0,5,"R","u",raw_value,0.01,con_value,"kWh",""],
[43,"MRST_DAY_DISCHARGED_H",33006,"ST",0,6,"R","u",raw_value,0.01,con_value,"kWh",""],
[44,"MRST_DAY_DISCHARGED_L",33007,"ST",0,7,"R","u",raw_value,0.01,con_value,"kWh",""],
[45,"MRST_MNT_CHARGED_H",33008,"ST",0,8,"R","u",raw_value,0.01,con_value,"kWh",""],
[46,"MRST_MNT_CHARGED_L",33009,"ST",0,9,"R","u",raw_value,0.01,con_value,"kWh",""],
[47,"MRST_MNT_DISCHARGED_H",33010,"ST",0,10,"R","u",raw_value,0.01,con_value,"kWh",""],
[48,"MRST_MNT_DISCHARGED_L",33011,"ST",0,11,"R","u",raw_value,0.01,con_value,"kWh",""],
[49,"MRST_INT_TEMP",35000,"TP",3,0,"R","u",raw_value,0.1,con_value,"°C",""],
[50,"MRST_MOS1_TEMP",35001,"TP",0,1,"R","u",raw_value,0.1,con_value,"°C",""],
[51,"MRST_MOS2_TEMP",35002,"TP",0,2,"R","u",raw_value,0.1,con_value,"°C",""],
[52,"MRST_MAX_CELL_TEMP",35010,"CT",2,0,"R","u",raw_value,0.1,con_value,"°C",""],
[53,"MRST_MIN_CELL_TEMP",35011,"CT",0,1,"R","u",raw_value,0.1,con_value,"°C",""],
[54,"MRST_INV_STATE",35100,"IS",1,0,"R","u",raw_value,1,con_value," ",""],
[55,"MRST_LIMIT_VOLT",35110,"LT",3,0,"R","u",raw_value,100,con_value,"mv",""],
[56,"MRST_LIMIT_CHARGE_CURR",35111,"LT",0,1,"R","u",raw_value,100,con_value,"ma",""],
[57,"MRST_LIMIT_DISCHARG_CURR",35112,"LT",0,2,"R","u",raw_value,100,con_value,"ma",""],
[58,"MRST_ALARM",36000,"AL",1,0,"R","b",raw_value,1,con_value," ","Alarm register"],
[59,"MRST_FAULT_LSB",36100,"FT",2,0,"R","b",raw_value,1,con_value," ","Fault register LSB"],
[60,"MRST_FAULT_MSB",36101,"FT",0,1,"R","b",raw_value,1,con_value," ","Fault register MSB"],
[61,"MRST_RESTART",41000,"RS",1,0,"RW","u",raw_value,1,con_value," ","0x55AA-->restart"],
[62,"MRST_UNIT_ID",41100,"UI",1,0,"RW","u",raw_value,1,con_value," ","unit id [1..255]"],
[63,"MRST_BACKUP",41200,"BK",1,0,"RW","u",raw_value,1,con_value," ","0:enable,1:disbale"],
[64,"MRST_RTU_MODE",42000,"RM",1,0,"RW","u",raw_value,1,con_value," ","0x55AA=ON, 0x55BB=OFF"],
[65,"MRST_INV_STATE",42010,"IV",2,0,"RW","u",raw_value,1,con_value," ","0:stop,1:charge,2:discharge"],
[66,"MRST_CHARGE_TO_SOC",42011,"IV",0,1,"RW","u",raw_value,1,con_value,"%","charge to target SOC"],
[67,"MRST_PWR_CHARGE",42020,"PW",2,0,"RW","u",raw_value,1,con_value,"W","range:[0..2500W]"],
[68,"MRST_PWR_DISCHARGE",42021,"PW",0,1,"RW","u",raw_value,1,con_value,"W","range:[0..2500W]"],
[69,"MRST_USER_MODE",43000,"UM",1,0,"RW","u",raw_value,1,con_value," ","0:manual,1:anti-feed,2:trade_mode"],
[70,"MRST_CHARGE_CUTOFF",44000,"CO",4,0,"RW","u",raw_value,0.1,con_value,"%","range:[80%..100%]"],
[71,"MRST_DISCHARGE_CUTOFF",44001,"CO",0,1,"RW","u",raw_value,0.1,con_value,"%","range:[12%..30%]"],
[72,"MRST_MAX_CHARGE_PWR",44002,"CO",0,2,"RW","u",raw_value,1,con_value,"W","range:[0..2500W]"],
[73,"MRST_MAX_DISCHARGE_PWR",44003,"CO",0,3,"RW","u",raw_value,1,con_value,"W","range:[0..2500W]"]
]

# --- Index for MARSTEK VENUS E fields ---- 
IDXM_INDX = 0   # - Index number in list 
IDXM_NAME = 1   # - Field name 
IDXM_ADDR = 2   # - Register address
IDXM_ABBR = 3   # - Group abbreviation 
IDXM_BLCK = 4   # - Block size (how many regs)
IDXM_OFFS = 5   # - Offset to start of block
IDXM_MODE = 6   # - Read amd/or Write register
IDXM_TYPE = 7   # - Variable type "char", "unsigned int", "signed int"
IDXM_RAWV = 8   # - Value (raw modbus word)
IDXM_GAIN = 9   # - Gain per unit
IDXM_CONV = 10  # - Value (converted and adjusted for gain)
IDXM_UNIT = 11  # - Unit
IDXM_DESC = 12  # - Description

# -----------------------------------------------------------------------------------------
# --- BATT thread -----------------------------------------------------------------------
# -----------------------------------------------------------------------------------------
    
def copy_marstek_to_batt(): 
    
    # --- Clear Device Name in BATT REG LIST : AC01..............
    globl.BATT_REGISTER_LIST[globl.BATT_DEVICE_NAME][globl.IDXB_CONV] = "" # clear string
    # --- Copy the Device Name block 10x --> 20 characters (bytes)
    for idxm in range(MRST_DEVICE_NAME, MARSTEK_MODBUS[MRST_DEVICE_NAME][IDXM_BLCK] + MRST_DEVICE_NAME): # + 1
        globl.BATT_REGISTER_LIST[globl.BATT_DEVICE_NAME][globl.IDXB_CONV] += MARSTEK_MODBUS[idxm][IDXM_CONV] # --- append str

    #--- Copy MRST_FW_VERSION
    globl.BATT_REGISTER_LIST[globl.BATT_FW_VERSION][globl.IDXB_CONV] = MARSTEK_MODBUS[MRST_FW_VERSION][IDXM_CONV]

    # --- Clear Serial Number in BATT REG LIST
    globl.BATT_REGISTER_LIST[globl.BATT_SERIAL_NUM][globl.IDXB_CONV] = "" # clear string
    # --- Copy the Serial Number block 10x --> 20 characters (bytes)
    for idxm in range(MRST_SERIAL_NUM, MARSTEK_MODBUS[MRST_SERIAL_NUM][IDXM_BLCK] + MRST_SERIAL_NUM ): # + 1
        globl.BATT_REGISTER_LIST[globl.BATT_SERIAL_NUM][globl.IDXB_CONV] += MARSTEK_MODBUS[idxm][IDXM_CONV] # --- append str

    # Now copy all converterd value registers 1 on 1 until MRST_TOT_CHARGED (2 regs)
    for idxm in range(MRST_DC_VOLT, MRST_BACKUP_PWR_VAL + 1):
        #--- Copy regs incl offset BATT REG (3) vs MARST_MODBUS (22) (22-3=19)
        offset = MRST_DC_VOLT - globl.BATT_DC_VOLT 
        globl.BATT_REGISTER_LIST[idxm-offset][globl.IDXB_CONV] = MARSTEK_MODBUS[idxm][IDXM_CONV]
   
    #--- Copy BATT_TOT_CHARGED -- Because these registers consist of 2 words...
    #globl.BATT_REGISTER_LIST[globl.BATT_TOT_CHARGED][globl.IDXB_CONV] = (MARSTEK_MODBUS[MRST_TOT_CHARGED_H][IDXM_CONV] + MARSTEK_MODBUS[MRST_TOT_CHARGED_L][IDXM_CONV]) * MARSTEK_MODBUS[MRST_TOT_CHARGED_L][IDXM_GAIN]
    #globl.BATT_REGISTER_LIST[globl.BATT_TOT_DISCHARGED][globl.IDXB_CONV] = (MARSTEK_MODBUS[MRST_TOT_DISCHARGED_H][IDXM_CONV] + MARSTEK_MODBUS[MRST_TOT_DISCHARGED_L][IDXM_CONV]) * MARSTEK_MODBUS[MRST_TOT_DISCHARGED_L][IDXM_GAIN]
    globl.BATT_REGISTER_LIST[globl.BATT_TOT_CHARGED][globl.IDXB_CONV] = "n.a."
    globl.BATT_REGISTER_LIST[globl.BATT_TOT_DISCHARGED][globl.IDXB_CONV] = "n.a."
    globl.BATT_REGISTER_LIST[globl.BATT_DAY_CHARGED][globl.IDXB_CONV] = "n.a."
    globl.BATT_REGISTER_LIST[globl.BATT_DAY_DISCHARGED][globl.IDXB_CONV] = "n.a."
    globl.BATT_REGISTER_LIST[globl.BATT_MNT_CHARGED][globl.IDXB_CONV] = "n.a."
    globl.BATT_REGISTER_LIST[globl.BATT_MNT_DISCHARGED][globl.IDXB_CONV] = "n.a."
    
    # Now copy all remaining registers until the end of the list
    for idxm in range(MRST_INT_TEMP, MRST_MAX_DISCHARGE_PWR + 1):
        #--- Copy regs incl offset BATT REG (24) vs MARST_MODBUS (49) (49-24=25)
        offset = MRST_INT_TEMP - globl.BATT_INT_TEMP
        globl.BATT_REGISTER_LIST[idxm-offset][globl.IDXB_CONV] = MARSTEK_MODBUS[idxm][IDXM_CONV]

# -----------------------------------------------------------------------------------------
# --- Convert all modbus register values in the MARSTEK_MODBUS list object CON_VALUE ------
# -----------------------------------------------------------------------------------------

def convert_modbus_registers():

    global MARSTEK_MODBUS

    # --- Loop through all the values in MARSTEK_MODBUS
    for reg_index in range(1, len(MARSTEK_MODBUS)): # --- start with 1 becaue of the header
        # --- Copy to local reg for ease of use
        reg_name = MARSTEK_MODBUS[reg_index][IDXM_NAME]
        reg_type = MARSTEK_MODBUS[reg_index][IDXM_TYPE]
        reg_rawv = MARSTEK_MODBUS[reg_index][IDXM_RAWV]
        reg_gain = MARSTEK_MODBUS[reg_index][IDXM_GAIN]
        reg_unit = MARSTEK_MODBUS[reg_index][IDXM_UNIT]
        # --- In case of binary error/fault register show bits
        if reg_type == "b":
            MARSTEK_MODBUS[reg_index][IDXM_CONV] = reg_rawv
        # --- In case of a char string register value
        elif reg_type == "c":
            byte_high = (reg_rawv >> 8) & 0xFF
            if byte_high < 33 or byte_high > 126: byte_high = 46 # --> "."
            byte_low  = reg_rawv & 0xFF
            if byte_low < 33 or byte_low > 126: byte_low = 46 # --> "."
            MARSTEK_MODBUS[reg_index][IDXM_CONV] = chr(byte_high) + chr(byte_low)
        # --- In case of an un signed register value
        elif reg_type == "u":
            MARSTEK_MODBUS[reg_index][IDXM_CONV] = reg_rawv * reg_gain
        # --- In case of a signed register value
        elif reg_type == "s":
            if reg_rawv > 0x7FFF: reg_rawv -= 0x10000 # subtrackt to get negative value
            MARSTEK_MODBUS[reg_index][IDXM_CONV] = reg_rawv * reg_gain
        else:
            MARSTEK_MODBUS[reg_index][IDXM_CONV] = reg_rawv * reg_gain
    
# -----------------------------------------------------------------------------------------

def copy_modbus_register_block(result, register_block): # --- Copy the register block (#regs)
    # --- Copy all modbus register values to MARSTEK_MODBUS list object RAW_VALUE
    global MARSTEK_MODBUS
    for reg_index in range(0, len(result.registers)): # --- start with 0 
        MARSTEK_MODBUS[register_block+reg_index][IDXM_RAWV] = result.registers[MARSTEK_MODBUS[register_block+reg_index][IDXM_OFFS]]
                
# -----------------------------------------------------------------------------------------

def print_modbus_registers(): # --- Print all registers in MARSTEK_MODBUS
    
    global MARSTEK_MODBUS
    
    if globl.show_mrst:
        
        print("[MRST] GR | NAME                     |  REG  | ADDR HEX | VAL HEX | VAL DEC | VAL CONV | UNIT | DESC .... ")
        print("[MRST] ---+--------------------------+-------+----------+---------+---------+----------+------+-----------")
        
        for reg_index in range(1, len(MARSTEK_MODBUS)): # --- start with 1 becaue of the header
            reg_name = MARSTEK_MODBUS[reg_index][IDXM_NAME]
            reg_addr = MARSTEK_MODBUS[reg_index][IDXM_ADDR]
            reg_abbr = MARSTEK_MODBUS[reg_index][IDXM_ABBR]
            reg_type = MARSTEK_MODBUS[reg_index][IDXM_TYPE]
            reg_rawv = MARSTEK_MODBUS[reg_index][IDXM_RAWV]
            reg_conv = MARSTEK_MODBUS[reg_index][IDXM_CONV]
            reg_unit = MARSTEK_MODBUS[reg_index][IDXM_UNIT]
            reg_desc = MARSTEK_MODBUS[reg_index][IDXM_DESC]

            if reg_type == "b": 
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>08b} | {reg_unit:<4} | {reg_desc}")
            elif reg_type == "c": 
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8} | {reg_unit:<4} | {reg_desc}")
            elif reg_type == "s" and isinstance(reg_conv, int):  
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8} | {reg_unit:<4} | {reg_desc}")
            elif reg_type == "s" and isinstance(reg_conv, float):  
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8.2f} | {reg_unit:<4} | {reg_desc}")
            elif reg_type == "u" and isinstance(reg_conv, int): 
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8} | {reg_unit:<4} | {reg_desc}")
            elif reg_type == "u" and isinstance(reg_conv, float): 
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8.2f} | {reg_unit:<4} | {reg_desc}")
            else:   
                print(f"[MRST] {reg_abbr} | {reg_name:<24} | {reg_addr:>5} |  0x{reg_addr:04X}  |  0x{reg_rawv:04X} | {reg_rawv:6}  | {reg_conv:>8} | {reg_unit:<4} | {reg_desc}")
                
        print("[MRST] ---+--------------------------+-------+----------+---------+---------+----------+------+-----------")

    
# -----------------------------------------------------------------------------------------
# --- BATT thread -----------------------------------------------------------------------
# -----------------------------------------------------------------------------------------

def batt_thread_fn(batt_stop_event: threading.Event, interval: float = 2.0):
    
    cntr = 0
    unit_id=1
    max_charge_pwr = 1600

    serial_port = "/dev/ttyUSB0"
    client = ModbusSerialClient(
        framer="rtu",
        port=serial_port,
        baudrate=115200,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1
    )

    while not batt_stop_event.is_set():
        
        if not client.connect():
            globl.log_debug(module_name, f"Could not connect to battery on {serial_port}")
            time.sleep(10)  # delay before reconnecting
            return
        globl.log_debug(module_name, f"Connected to battery on {serial_port}")
        
        try:
            while not batt_stop_event.is_set():

                # --- Device Name
                reg_block = MRST_DEVICE_NAME
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)
                    
                # --- FW version
                reg_block = MRST_FW_VERSION
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- SERIAL number
                reg_block = MRST_SERIAL_NUM
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- DC block
                reg_block = MRST_DC_VOLT
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- AC block
                reg_block = MRST_AC_VOLT
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- BACKUP block
                reg_block = MRST_BACKUP_VOLT
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # ---  Statistics block 
                reg_block = MRST_TOT_CHARGED
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- INTernal TEMP (mosfets)
                reg_block = MRST_INT_TEMP
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- CELL TEMP MAX and MIN value block
                reg_block = MRST_MAX_CELL_TEMP
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- INVerter STATE block
                reg_block = MRST_INV_STATE
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- ALARM WORD
                reg_block = MRST_ALARM
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- FAULT DOUBLE WORD
                reg_block = MRST_FAULT_LSB
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- READ and WRITE registers -- SET values after setting RTU mode to 0x55AA = ON (0x55BB = OFF) 
                
                # --- RESTART --- write 0x55AA
                reg_block = MRST_RESTART
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- UNIT_ID - be careful not to change the Unit ID
                reg_block = MRST_UNIT_ID
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- MRST_BACKUP - 0: enable backup, 1: disable backup
                reg_block = MRST_BACKUP
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- RTU MODE setting RTU mode to 0x55AA = ON (0x55BB = OFF) 
                reg_block = MRST_RTU_MODE
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- INVerter STATE - 0:stop, 1:charge, 2:discharge
                reg_block = MRST_INV_STATE
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- PWR_CHARGE - charging and discharging power [0-2500W]
                reg_block = MRST_PWR_CHARGE
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- USER_MODE - 0:manual, 1:anti-feed, 2:trade mode
                reg_block = MRST_USER_MODE
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- CHARGE and DISCHARGE CUTOFF + MRST_MAX_CHARGE_PWR + MRST_MAX_DISCHARGE_PWR
                reg_block = MRST_CHARGE_CUTOFF
                result = client.read_holding_registers(address=MARSTEK_MODBUS[reg_block][IDXM_ADDR], count=MARSTEK_MODBUS[reg_block][IDXM_BLCK], device_id=unit_id)
                if result.isError():
                    globl.log_debug(module_name, f"Read error: {result}")
                else: # copy modbus registers in MARSTEK_MODBUS list object
                    copy_modbus_register_block(result, reg_block)

                # --- Convert all MODBUS registers and adjust gain
                convert_modbus_registers()

                # --- Copy MARSTEK MODBUS LIST to BATT_REGISTER_LIST with Thread.Lock
                copy_marstek_to_batt()
                
                # --- Print all MODBUS registers
                print_modbus_registers()

                # --- 
                #max_charge_pwr = max_charge_pwr + 1
                #result = client.write_register(address=44002, value=max_charge_pwr, device_id=unit_id)

                cntr += 1      # increment counter
                time.sleep(2)  # delay between reads (interval)
                globl.log_debug(module_name, f"Loop counter: {cntr}")
                
        except Exception as e:
            globl.log_debug(module_name, f"Exception: {e}")
            time.sleep(2)  # delay between reads after error
        finally:
            client.close()
            globl.log_debug(module_name, "Battery connection closed.")
        

#!/usr/bin/env python3
"""
main.py

Simple multi-threaded CLI that starts 5 threads:
  1) BATT - Modbus RTU client over ttyUSB0 (uses pymodbus to communicate with the Marstek Venus E v2.0)
  2) DSMR - Dutch Smart Meter client connects to port 23 reading DSMR P1 data
  3) BSLD - Baseload reader (every 10s) checking for changes in base load file
  4) LOG  - CSV logger - writes every x sec to the CSV log file
  5) EMS  - EMS thread (every 1s) doing calculations

Usage: run the script and use the CLI commands:
  start all     - start all threads
  start batt    - start ems thread
  start dsmr    - start ems thread
  start bsld    - start ems thread
  start log     - start ems thread
  start ems     - start ems thread
  stop all      - stop all threads
  stop batt     - stop ems thread
  stop dsmr     - stop ems thread
  stop bsld     - stop ems thread
  stop log      - stop ems thread
  stop ems      - stop ems thread
  show ...      - show status of ...
  set ...       - set value ...
  exit          - stops and exits

baseline chatGPT python prompt:
write a multi threaded command line interface program using SimpleCLI 
that starts 5 individual threads: where 
thread 1 connects to a modbus master RTU over ttyUSB0, 
thread 2 is a TCP client that connects to a server on port 23 and received DSMR P1 data and 
thread 3 reads the Baseload csv file every 10 seconds and checks if the the base load data has changed, 
thread 4 writes log data to a csv file every 4 seconds and 
thread 5 is the energy management system (ems) thread that makes calculations and executes every second. 
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
import globl   # -- import global constants

from batt import batt_thread_fn
from dsmr import dsmr_thread_fn
from bsld import baseload_thread_fn
from logger import logger_thread_fn
from ems import ems_thread_fn

from typing import Optional
from datetime import datetime
from pymodbus.client import ModbusSerialClient

# -----------------------------------------------------------------
module_name = "MAIN"
# -----------------------------------------------------------------

# -----------------------------------------------------------------------------
# --- CONST -------------------------------------------------------------------
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# ---- Configurable defaults --------------------------------------------------
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# --- Shared global data (protected by locks) ---------------------------------
# -----------------------------------------------------------------------------

# initializing the header and data list for baseload
#baseload_header = []
#baseload_data = []

str_telegram = "/ISK5\2M550T-1012"  # hold the incoming p1 telegram as a string

# ---- Protected by locks -----------------------------------------------------

#batt_lock = threading.Lock()
#dsmr_lock = threading.Lock()
#base_lock = threading.Lock()
#ems_lock = threading.Lock()

# -----------------------------------------------------------------------------
# ---- Global thread control --------------------------------------------------
# -----------------------------------------------------------------------------

threads = {}

batt_stop_event = threading.Event()     # baseload stop signal
dsmr_stop_event  = threading.Event()    # baseload stop signal
bsld_stop_event = threading.Event()     # baseload stop signal
log_stop_event = threading.Event()      # logger stop signal
ems_stop_event = threading.Event()      # ems stop signal


# -----------------------------------------------------------------------------
# ---- Thread processes -------------------------------------------------------
# -----------------------------------------------------------------------------

# --- batt_thread_fn is moved to file: batt.py 
# --- dsmr_thread_fn moved to file: dsmr.py 
# --- baseload_thread_fn moved to file: bsld.py
# --- logger_thread_fn moved to file: logger.py
# --- ems_thread_fn moved to file: ems.py
        
# -----------------------------------------------------------------------------
# ---- SimpleCLI class --------------------------------------------------------
# -----------------------------------------------------------------------------

class SimpleCLI:
    
    prompt = "ems> "

    def __init__(self):
        self.running = False

# -----------------------------------------------------------------------------
# ---- START ------------------------------------------------------------------
# -----------------------------------------------------------------------------
# --- ToDo : Threads can be started multiple time and that should not happen --
# -----------------------------------------------------------------------------

    def start_all(self):

        # clear all stop event flags    
        batt_stop_event.clear()
        dsmr_stop_event.clear()
        bsld_stop_event.clear()
        log_stop_event.clear()
        ems_stop_event.clear()
        
        # spawn threads
        t1 = threading.Thread(target=batt_thread_fn, name="batt-thread", args=(batt_stop_event, 1.0), daemon=True)
        t2 = threading.Thread(target=dsmr_thread_fn, name="dsmr-thread", args=(dsmr_stop_event, 1.0), daemon=True)
        t3 = threading.Thread(target=baseload_thread_fn, name="baseload-thread", args=(bsld_stop_event, 1.0), daemon=True)
        t4 = threading.Thread(target=logger_thread_fn, name="logger-thread", args=(log_stop_event, 1.0), daemon=True)
        t5 = threading.Thread(target=ems_thread_fn, name="ems-thread", args=(ems_stop_event, 1.0), daemon=True)
        
        # store threads in a dictionary
        threads["BATT"] = t1
        threads["DSMR"] = t2
        threads["BSLD"] = t3
        threads["LOG"] = t4
        threads["EMS"] = t5

        t1.start()
        globl.log_debug(module_name, f"Starting Battery process -> {t1.name} (daemon={t1.daemon})")
        t2.start()
        globl.log_debug(module_name, f"Starting Smart Meter process -> {t2.name} (daemon={t2.daemon})")
        t3.start()
        globl.log_debug(module_name, f"Starting Baseload process -> {t3.name} (daemon={t3.daemon})")
        t4.start()
        globl.log_debug(module_name, f"Starting Logger process -> {t4.name} (daemon={t4.daemon})")
        t5.start()
        globl.log_debug(module_name, f"Starting Energy Management System process -> {t5.name} (daemon={t5.daemon})")

    def start_batt(self):
        batt_stop_event.clear()
        t1 = threading.Thread(target=batt_thread_fn, name="batt-thread", args=(batt_stop_event, 1.0), daemon=True)
        threads["BATT"] = t1
        t1.start()
        globl.log_debug(module_name, f"Started {t1.name} (daemon={t1.daemon})")
        
    def start_dsmr(self):
        dsmr_stop_event.clear()
        t2 = threading.Thread(target=dsmr_thread_fn, name="dsmr-thread", args=(dsmr_stop_event, 1.0), daemon=True)
        threads["DSMR"] = t2
        t2.start()
        globl.log_debug(module_name, f"Started {t2.name} (daemon={t2.daemon})")

    def start_baseload(self):
        bsld_stop_event.clear()
        t3 = threading.Thread(target=baseload_thread_fn, name="baseload-thread", args=(bsld_stop_event, 1.0), daemon=True)
        threads["BSLD"] = t3
        t3.start()
        globl.log_debug(module_name, f"Started {t3.name} (daemon={t3.daemon})")

    def start_logger(self):
        log_stop_event.clear()
        t4 = threading.Thread(target=logger_thread_fn, name="logger-thread", args=(log_stop_event, 1.0), daemon=True)
        threads["LOG"] = t4
        t4.start()
        globl.log_debug(module_name, f"Started {t4.name} (daemon={t4.daemon})")

    def start_ems(self):
        ems_stop_event.clear()
        t5 = threading.Thread(target=ems_thread_fn, name="ems-thread", args=(ems_stop_event, 1.0), daemon=True)
        threads["EMS"] = t5
        t5.start()
        globl.log_debug(module_name, f"Started {t5.name} (daemon={t5.daemon})")
        
    def start(self, process):
        if process.strip() == "all":
            self.start_all()
        elif process.strip() == "batt":
            self.start_batt()
        elif process.strip() == "dsmr":
            self.start_dsmr()
        elif process.strip() == "bsld":
            self.start_baseload()
        elif process.strip() == "log":
            self.start_logger()
        elif process.strip() == "ems":
            self.start_ems()
        else:
            print(f"Unknown start command: (type 'help')")
            print("  start all")
            print("  start batt")
            print("  start dsmr")
            print("  start bsld")
            print("  start log")
            print("  start ems")
        
# -----------------------------------------------------------------------------
# ---- STOP -------------------------------------------------------------------
# -----------------------------------------------------------------------------

    def stop_all(self):
        
        # load threads 
        t1 = threads["BATT"]
        t2 = threads["DSMR"]
        t3 = threads["BSLD"]
        t4 = threads["LOG"]
        t5 = threads["EMS"]
        
        # stop all threads
        batt_stop_event.set()
        dsmr_stop_event.set()
        bsld_stop_event.set()
        log_stop_event.set()
        ems_stop_event.set()
        
        # stop batt/modbus thread
        if t1.is_alive():
            globl.log_debug(module_name, f"Stopping {t1.name} ...")
            #batt_stop_event.set()
            t1.join(timeout=5.0)
            if t1.is_alive(): 
                globl.log_debug(module_name, f"{t1.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t1.name} Stopped.")
                threads.pop(t1.name, None)
        # stop dsmr thread
        if t2.is_alive():
            globl.log_debug(module_name, f"Stopping {t2.name} ...")
            #dsmr_stop_event.set()
            t2.join(timeout=5.0)
            if t2.is_alive(): 
                globl.log_debug(module_name, f"{t2.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t2.name} Stopped.")
                threads.pop(t2.name, None)
        # stop baseload thread
        if t3.is_alive():
            globl.log_debug(module_name, f"Stopping {t3.name} ...")
            #bsld_stop_event.set()
            t3.join(timeout=5.0)
            if t3.is_alive(): 
                globl.log_debug(module_name, f"{t3.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t3.name} Stopped.")
                threads.pop(t3.name, None)
        # stop logger thread
        if t4.is_alive():
            globl.log_debug(module_name, f"Stopping {t4.name} ...")
            #log_stop_event.set()
            t4.join(timeout=5.0)
            if t4.is_alive(): 
                globl.log_debug(module_name, f"{t4.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t4.name} Stopped.")
                threads.pop(t4.name, None)
        # stop ems thread
        if t5.is_alive():
            globl.log_debug(module_name, f"Stopping {t5.name} ...")
            #ems_stop_event.set()
            t5.join(timeout=5.0)
            if t5.is_alive(): 
                globl.log_debug(module_name, f"{t5.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t5.name} Stopped.")
                threads.pop(t5.name, None)
        
        # clear all stop event flags    
        batt_stop_event.clear()
        dsmr_stop_event.clear()
        bsld_stop_event.clear()
        log_stop_event.clear()
        ems_stop_event.clear()

    def stop_batt(self):
        t1 = threads["BATT"]
        if t1.is_alive():
            globl.log_debug(module_name, f"Stopping {t2.name} ...")
            batt_stop_event.set()
            t1.join(timeout=5.0)
            if t1.is_alive(): 
                globl.log_debug(module_name, f"{t1.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t1.name} Stopped.")
                threads.pop(t1.name, None)
        else:
            globl.log_debug(module_name, f"This thread is not running...")
        batt_stop_event.clear()

    def stop_dsmr(self):
        t2 = threads["DSMR"]
        if t2.is_alive():
            globl.log_debug(module_name, f"Stopping {t2.name} ...")
            dsmr_stop_event.set()
            t2.join(timeout=5.0)
            if t2.is_alive(): 
                globl.log_debug(module_name, f"{t2.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t2.name} Stopped.")
                threads.pop(t2.name, None)
        else:
            globl.log_debug(module_name, f"This thread is not running...")
        dsmr_stop_event.clear()

    def stop_baseload(self):
        t3 = threads["BSLD"]
        if t3.is_alive():
            globl.log_debug(module_name, f"Stopping {t3.name} ...")
            bsld_stop_event.set()
            t3.join(timeout=5.0)
            if t3.is_alive(): 
                globl.log_debug(module_name, f"{t3.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t3.name} Stopped.")
                threads.pop(t3.name, None)
        else:
            globl.log_debug(module_name, f"This thread is not running...")
        bsld_stop_event.clear()

    def stop_logger(self):
        t4 = threads["LOG"]
        if t4.is_alive():
            globl.log_debug(module_name, f"Stopping {t4.name} ...")
            log_stop_event.set()
            t4.join(timeout=5.0)
            if t4.is_alive(): 
                globl.log_debug(module_name, f"{t4.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t4.name} Stopped.")
                threads.pop(t4.name, None)
        else:
            globl.log_debug(module_name, f"This thread is not running...")
        log_stop_event.clear()

    def stop_ems(self):
        t5 = threads["EMS"]
        if t5.is_alive():
            globl.log_debug(module_name, f"Stopping {t5.name} ...")
            ems_stop_event.set()
            t5.join(timeout=5.0)
            if t5.is_alive(): 
                globl.log_debug(module_name, f"{t5.name} did not exit within timeout.")
            else:
                globl.log_debug(module_name, f"{t5.name} Stopped.")
                threads.pop(t5.name, None)
        else:
            globl.log_debug(module_name, f"This thread is not running...")
        ems_stop_event.clear()


    def stop(self, process):
        if process.strip() == "all":
            self.stop_all()
        elif process.strip() == "batt":
            self.stop_batt()
        elif process.strip() == "dsmr":
            self.stop_dsmr()
        elif process.strip() == "bsld":
            self.stop_baseload()
        elif process.strip() == "log":
            self.stop_logger()
        elif process.strip() == "ems":
            self.stop_ems()
        else:
            print("Unknown stop command: (type 'help')")
            print("  stop all")
            print("  stop batt")
            print("  stop dsmr")
            print("  stop bsld")
            print("  stop log")
            print("  stop ems")

# -----------------------------------------------------------------------------
# ---- SHOW -------------------------------------------------------------------
# -----------------------------------------------------------------------------

    # --- debug --- 
    def show_all(self):
        
        # load threads 
        #t1 = threads["BATT"]
        #t2 = threads["DSMR"]
        #t3 = threads["BSLD"]
        #t4 = threads["LOG"]
        #t5 = threads["EMS"]
        
        # stop all threads
        #batt_stop_event.set()
        #dsmr_stop_event.set()
        #bsld_stop_event.set()
        #log_stop_event.set()
        #ems_stop_event.set()

        for thread in threads:
            print(f"thread: {thread}")
        
        # updated in dsmr and made available via global variables in globl.py
        # - globl.power_cons 
        # - globl.power_prod 
        print(f"[MAIN] globl.power_cons: {globl.power_cons} Watt")
        print(f"[MAIN] globl.power_prod: {globl.power_prod} Watt\n")

    # --- show converted battery (=marstek) values ------------------------------------ 
    
    def show_batt(self):
        
        print("[BATT] GR | NAME                     |                VALUE | UNIT | DESC .... ")
        print("[BATT] ---+--------------------------+----------------------+------+------------------")

        for indx in range(1, len(globl.BATT_REGISTER_LIST)): # --- start with 1 becaue of the header
        #for indx in range(4, 10): # --- start with 1 because of the header    
            reg_name = globl.BATT_REGISTER_LIST[indx][globl.IDXB_NAME]
            reg_abbr = globl.BATT_REGISTER_LIST[indx][globl.IDXB_ABBR]
            reg_conv = globl.BATT_REGISTER_LIST[indx][globl.IDXB_CONV]
            reg_unit = globl.BATT_REGISTER_LIST[indx][globl.IDXB_UNIT]
            reg_desc = globl.BATT_REGISTER_LIST[indx][globl.IDXB_DESC]
            if isinstance(reg_conv, float):
                print(f"[BATT] {reg_abbr} | {reg_name:<24} | {reg_conv:>20.2f} | {reg_unit:<4} | {reg_desc}")
            else:
                print(f"[BATT] {reg_abbr} | {reg_name:<24} | {reg_conv:>20} | {reg_unit:<4} | {reg_desc}")
                
        print("[BATT] ---+--------------------------+----------------------+------+------------------")

    # --- show converted home (=dsmr) values ------------------------------------ 

    def show_home(self):

        print("[HOME] GR | NAME                     | VALUE | UNIT | DESC .... ")
        print("[HOME] ---+--------------------------+-------+------+------------------")




    # ---------------------
        
    def show(self, argument):
        if argument.strip() == "all":
            self.show_all()
        elif argument.strip() == "batt":
            self.show_batt()
        elif argument.strip() == "home":
            self.show_home()
        else:
            print(f"Unknown show command: (type 'help')")
            print("  show all")
            print("  show batt")
            print("  show home")

            
    def toggle(self, argument):
        if argument.strip() == "mrst":
            globl.log_debug(module_name, "Toggle Marstek modbus data...")
            globl.show_mrst = not globl.show_mrst
        elif argument.strip() == "dsmr":
            globl.log_debug(module_name, "Toggle DSMR (P1) data...")
            globl.show_dsmr = not globl.show_dsmr
        elif argument.strip() == "bsld":
            globl.log_debug(module_name, "Toggle Baseload data...")
            globl.show_bsld = not globl.show_bsld
        elif argument.strip() == "debug":
            globl.log_debug(module_name, "Toggle DEBUG data...")
            globl.show_debug = not globl.show_debug
        else:
            print(f"unknown toggle argument: (type 'help')")
            print("  toggle mrst")
            print("  toggle dsmr")
            print("  toggle bsld")
            #print("  toggle log")
            #print("  toggle ems")
            print("  toggle debug")

# -----------------------------------------------------------------------------
# ---- RUN SimpleCLI --------------------------------------------------------
# -----------------------------------------------------------------------------

    def run(self):

        print("SimpleCLI for EMS. Type 'help' or '?' for commands.")
        
        globl.log_debug(module_name, "Starting all threads...")
        self.start_all()
        
        while True:

            try:
                cmdline = input(self.prompt).strip()
            except (EOFError, KeyboardInterrupt):
                globl.log_debug(module_name, f"\n\n Exiting (caught interrupt)... \n\n")
                self.stop_all()
                break
            if not cmdline:
                continue

            parts = cmdline.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in ("exit", "quit"):
                self.stop_all()
                globl.log_debug(module_name, f"bye...")
                break
                
            elif cmd in ("help", "?"):
                print("commands:")
                print("  start ... - start threads")
                print("  stop ... - stop threads")
                print("  show ... - batt, home")
                print("  toggle ... - show mrst, dsmr, bsld...")
                print("  help - show this help")
                print("  exit - stop and exit")
                
            elif cmd == "start":
                if len(args) == 1:
                    self.start(args[0])
                
            elif cmd == "stop":
                if len(args) == 1:
                    self.stop(args[0])
                    
            elif cmd == "show":
                if len(args) == 1:
                    self.show(args[0])

            elif cmd == "toggle":
                if len(args) == 1:
                    self.toggle(args[0])

            else:
                print(f"Unknown command: {cmd} (type 'help')")


# --------------------------------------------------------------------------------------
# ---- MAIN()---------------------------------------------------------------------------
# --------------------------------------------------------------------------------------

def main():
    cli = SimpleCLI()
    try:
        cli.run()
    except Exception as e:
        globl.log_debug(module_name, f"Exception error: {e}")
        try:
            cli.stop_all()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()


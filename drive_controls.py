# -*- coding: utf-8 -*-
"""
Created on Tue Nov 11 16:14:19 2014

@author: Sean
"""

from ctypes import *
from threading import Thread

# For sleep()
import time
import numpy as np
import msvcrt
import signal


def run_drive_controls(control_file):
    # -------------------------------------------------------------------------
    # dll initialization
    # -------------------------------------------------------------------------
    # Load canlib32.dll
    canlib32 = windll.canlib32
    
    # Load the API functions we use from the dll
    canInitializeLibrary = canlib32.canInitializeLibrary
    canOpenChannel = canlib32.canOpenChannel
    canBusOn = canlib32.canBusOn
    canBusOff = canlib32.canBusOff
    canClose = canlib32.canClose
    canWrite = canlib32.canWrite
    canRead = canlib32.canRead
    canGetChannelData = canlib32.canGetChannelData
    
    # A few constants from canlib.h
    canCHANNELDATA_CARD_FIRMWARE_REV = 9
    canCHANNELDATA_DEVDESCR_ASCII = 26
    
    
    # Define a type for the body of the CAN message. Eight bytes as usual.
    MsgDataType = c_uint8 * 8
    
    # Initialize the library...
    canInitializeLibrary()
    
    # ... and open channels 0 and 1. These are assumed to be on the same
    # terminated CAN bus.
    hnd1 = canOpenChannel(c_int(0), c_int(32))
    
    # Go bus on
    stat = canBusOn(c_int(hnd1))
    if stat < 0: 
        print "canBusOn channel 1 failed: ", stat
        assert(0)
    
    # Setup a message
    msg = MsgDataType()
    
    
    # Obtain the firmware revision for channel (not handle!) 0
    fw_rev = c_uint64()
    canGetChannelData(c_int(0), canCHANNELDATA_CARD_FIRMWARE_REV, pointer(fw_rev), 8)
    print "Firmware revision channel 0 = ", (fw_rev.value >> 48), ".", (fw_rev.value >> 32) & 0xFFFF, ".", (fw_rev.value) & 0xFFFF
    
    # Obtain device name for channel (not handle!) 0
    s = create_string_buffer(100)
    canGetChannelData(c_int(0), canCHANNELDATA_DEVDESCR_ASCII, pointer(s), 100)
    print "Device name: ", s.value
       
    
    test = (int)(raw_input("Enter the test # to start on (bypasses all tests before input): "))    
    
    controls_input = np.loadtxt(control_file, dtype="int", delimiter=',', skiprows=1)
    print controls_input

    if test > controls_input[-1,2]:
        print "Error! Test input does not exist in the drive controls file"
        return
    
    line = 0
    print controls_input[line,2]
    KillSwitch = False  
    
    try:
        while line < len(controls_input[:,2]):
            if test == controls_input[line,2]:
                #Continue performing current test
                print "RPM is ", controls_input[line,0]
                print "Torque is ", controls_input[line,1]
                
                try:
                    '''
                    id, msg, dlc, flg, time = ch1.read()
                    print "%9d  %9d  0x%02x  %d  %s" % (id, time, flg, dlc, msg)
                    for i in range(dlc):
                        msg[i] = (msg[i]+1) % 256
                    ch1.write(id, msg, flg)
                    '''
                    for i in range(100 * 5):
                        time.sleep(0.01)
                except:
                    try:
                        print "COMMANDING ZERO TORQUE + ZERO SPEED"
                        stat = canWrite(c_int(hnd1), c_int(0), pointer(msg), c_int(2), c_int(0))
                        KillSwitch = True
                    except KeyboardInterrupt:
                        pass
    
            elif test < controls_input[line,2]:
                #Prompt to continue test, increment test variable
                char = 'temp'
                
                print "Please set the dyno to ", controls_input[line,0], "\n"
                while char != '':
                    char = raw_input("Hit the enter key to continue to the next test")
                test += 1
            if KillSwitch:
                break
                
            line += 1
    except None:
        pass
    # Some cleanup, which would be done automatically when the DLL unloads.
    stat = canBusOff(c_int(hnd1))
    
    canClose(c_int(hnd1))
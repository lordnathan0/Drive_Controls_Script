# -*- coding: utf-8 -*-
"""
Created on Tue Nov 11 16:14:19 2014

@author: Sean
"""

from ctypes import *
from threading import Thread
import struct

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

    if test > controls_input[-1,3]:
        print "Error! Test input does not exist in the drive controls file"
        return
    
    line = 0
    index = 0
    
    try:
        while line < len(controls_input[:,3]):
            if test == controls_input[line,3]:
                #Continue performing current test
                print "RPM is ", controls_input[line,1]
                print "Torque is ", controls_input[line,2]

                current = (float(controls_input[line,2]))/300.0
                '''
                Take float, "pack" into bytes (represented using strings). Takes each byte string and converts to an integer that is
                stored in highBytes
                '''
                
                msg[0] = (controls_input[line,1] & 0xFF)
                msg[1] = (controls_input[line,1] & 0xFF00) >> 8
                msg[2] = (controls_input[line,1] & 0xFF0000) >> 16
                msg[3] = (controls_input[line,1] & 0xFF000000) >> 24
                
                highBytes = [ord(byte) for byte in struct.pack('!f', current)]
                msg[4] = highBytes[3]
                msg[5] = highBytes[2]
                msg[6] = highBytes[1]
                msg[7] = highBytes[0]                
                
                try:
                    
                    for i in range(100 * controls_input[line,0]):
                        time.sleep(0.01)
                        stat = canWrite(c_int(hnd1), 401, pointer(msg), c_int(8), c_int(0))
                        
                    
                except KeyboardInterrupt:
                    try:
                        print "COMMANDING ZERO TORQUE + ZERO SPEED"
                        index = 0
                        while index < 8:
                            msg[index] = 0
                            index += 1
                        stat = canWrite(c_int(hnd1), 0x401, pointer(msg), c_int(8), c_int(0))
                        raw_input("Please hit enter to continue the test ...")
                    except:
                        index = 0
                        while index < 8:
                            msg[index] = 0
                        stat = canWrite(c_int(hnd1), 0x401, pointer(msg), c_int(8), c_int(0))
    
            elif test < controls_input[line,3]:
                #Prompt to continue test, increment test variable
                char = 'temp'
                
                print "Please set the dyno to ", controls_input[line,1], "\n"
                while char != '':
                    char = raw_input("Hit the enter key to continue to the next test")
                test += 1
                line -= 1
                
            line += 1
    except None:
        pass
    
    # Command 0 current and 0 RPM before exiting from the bus.
    while index < 8:
        msg[index] = 0
        index += 1
    stat = canWrite(c_int(hnd1), 0x401, pointer(msg), c_int(8), c_int(0))
    # Some cleanup, which would be done automatically when the DLL unloads.
    stat = canBusOff(c_int(hnd1))
    
    canClose(c_int(hnd1))
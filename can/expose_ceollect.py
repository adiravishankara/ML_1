#!/usr/bin/python3
import tkinter as tk
from tkinter import messagebox
import sys
import datetime
from pathlib import Path
import os
import _thread
import tkinter.ttk as ttk
import RPi.GPIO as GPIO
import time
import numpy as np
import time
import Adafruit_ADS1x15

# Create an ADS1115 ADC (16-bit) instance.
adc = Adafruit_ADS1x15.ADS1115()

# Choose a gain of 1 for reading voltages from 0 to 4.09V.
# Or pick a different gain to change the range of voltages that are read:
#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
# See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
GAIN = 2 / 3

# Variable Declarations
sensor_input_channel_1 = 2 # Pin on ADC used to read analog signal from first sensor in dual channel sensor
sensor_input_channel_2 = 1 # Pin on ADC used to read analog signal from second sensor in dual channel sensor
linear_actuator_position_channel = 0 # Pin on ADC used to read analog signal from linear actuator internal position sensor

pumping_time = 20 # time allowed for vacuum pump to draw sample air
flow_stabilization_time = 2 # time allowed for air to settle after vacuum pump is shut off
sensing_delay_time = 1 # time delay after beginning data acquisition till when the sensor is exposed to sample
sensing_retract_time = 7 # time allowed before sensor is retracted, no longer exposed to sample
duration_of_signal = 10 # time allowed for data acquisition per test run
extended_state = 2.6 # voltage value achieved when linear actuator is extended to correct sensing depth
retracted_state = 1.5 # voltage value achieved when linear actuator is retracted to idle state
sampling_time = 0.1 # time between samples taken, determines sampling frequency
printing_time = 1

#------------------------Pin definitions------------------------#
# Pin Definitions:
vacuum_pump = 17 # Broadcom pin 17 (P1 pin 11)
linear_actuator_extend = 27 # Broadcom pin 5 (P1 pin 13)
linear_actuator_unlock_retract = 22 # Broadcom pin 12 (P1 pin 15)

#---------------------------------------------------------------------#
# Pin Setup:
GPIO.setmode(GPIO.BCM)    # There are two options for this, but just use the board one for now. Don't worry much about it, we can check the definitions when I get back
GPIO.setup(linear_actuator_extend, GPIO.OUT) # Specifies linear_actuator_extend pin as an output
GPIO.setup(linear_actuator_unlock_retract, GPIO.OUT) # Specifies linear_actuator_unlock_retract pin as an output

# Initial state for outputs:
GPIO.output(linear_actuator_extend, GPIO.LOW)
GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)


def exposeAndCollectData():
    global stopCounter
    start_time = time.time()  # capture the time at which the test began. All time values can use start_time as a reference
    dataVector1 = []  # data values to be returned from sensor 1
    dataVector2 = []  # data values to be returned from sensor 2
    timeVector = []  # time values associated with data values
    sampling_time_index = 1  # sampling_time_index is used to ensure that sampling takes place every interval of sampling_time, without drifting.

    print("Starting data capture")

    while (time.time() < (start_time + duration_of_signal)):  # While time is less than duration of logged file
        if (time.time() > (start_time + (
                sampling_time * sampling_time_index))):  # if time since last sample is more than the sampling time, take another sample
            print("get another sample")
            dataVector1.append(adc.read_adc(sensor_input_channel_1,
                                            gain=GAIN))  # Perform analog to digital function, reading voltage from first sensor channel
            dataVector2.append(adc.read_adc(sensor_input_channel_2,
                                            gain=GAIN))  # Perform analog to digital function, reading voltage from second sensor channel
            timeVector.append(time.time() - start_time)
            sampling_time_index += 1
            print(ADC_linear_actuator())
            # increment sampling_time_index to set awaited time for next data sample
        # if ((sampling_time_index - 1) % 10 == 0):
        #                          print(int(time.time() - start_time))

        # If time is between 10-50 seconds and the Linear Actuator position sensor signal from the ADC indicates a retracted state, extend the sensor
        elif (time.time() >= (start_time + sensing_delay_time) and time.time() <= (
                sensing_retract_time + start_time) and ADC_linear_actuator() < extended_state):
##            print("extend actuator")
            GPIO.output(linear_actuator_extend, GPIO.HIGH)  # Actuate linear actuator to extended position
            GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)  # Energizing both control wires causes linear actuator to extend

        # If time is less than 10 seconds or greater than 50 seconds and linear actuator position sensor signal from the ADC indicates an extended state, retract the sensor
        elif (((time.time() < (sensing_delay_time + start_time)) or (
                time.time() > (sensing_retract_time + start_time))) and ADC_linear_actuator() > retracted_state):
##            print("retract actuator")
            GPIO.output(linear_actuator_unlock_retract,GPIO.HIGH)  # Retract linear actuator to initial position. Energizing only the linear_actuator_unlock_retract wire causes the linear actuator to retract
            GPIO.output(linear_actuator_extend, GPIO.LOW)
        # Otherwise, keep outputs off
        else:
            GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)
            GPIO.output(linear_actuator_extend, GPIO.LOW)
            
    return dataVector1, dataVector2, timeVector

def ADC_linear_actuator():
    conversion_value = (adc.read_adc(linear_actuator_position_channel,gain=GAIN)/pow(2, 15))*6.144
    return conversion_value

dv1, dv2, tv = exposeAndCollectData()
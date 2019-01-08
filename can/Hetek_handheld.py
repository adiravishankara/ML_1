#	This program is designed to automate the data collection process for the ATFL HETEK Project.
#	Developed by Matthew Barriault and Isaac Alexander


# Imports
import RPi.GPIO as GPIO
import time
import numpy as np
from pathlib import Path
import datetime
import os
import Adafruit_ADS1x15

#------------------------Variable Declarations------------------------#
sensing_delay_time = 1 # time delay after beginning data acquisition till when the sensor is exposed to sample
sensing_retract_time = 5 # time allowed before sensor is retracted, no longer exposed to sample
duration_of_signal = 10 # time allowed for data acquisition per test run
extended_state = 1.9 # voltage value achieved when linear actuator is extended to correct sensing depth
retracted_state = 1.3 # voltage value achieved when linear actuator is retracted to idle state
sampling_time = 0.1 # time between samples taken, determines sampling frequency
printing_time = 1

#---------------------------------------------------------------------#
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 1

pump_pin = 17
linear_actuator_extend = 27
linear_actuator_retract = 22

# Pin Setup:
GPIO.setmode(GPIO.BCM)
GPIO.setup(pump_pin, GPIO.OUT)
GPIO.setup(linear_actuator_extend, GPIO.OUT)
GPIO.setup(linear_actuator_retract, GPIO.OUT)


# Initial state for outputs:
GPIO.output(pump_pin, GPIO.LOW)
GPIO.output(linear_actuator_extend, GPIO.LOW)
GPIO.output(linear_actuator_retract, GPIO.LOW)

#------------------------Function definitions------------------------#
def exposeAndCollectData():
    start_time = time.time() # capture the time at which the test began. All time values can use start_time as a reference
    dataVector1 = [] # data values to be returned from sensor 1
    dataVector2 = [] # data values to be returned from sensor 2
    timeVector = []

    sampling_time_index = 1 #sampling_time_index is used to ensure that sampling takes place every interval of sampling_time, without drifting.
    data_date_and_time = time.asctime( time.localtime(time.time()) ) 
    print("Starting data capture")
            
    while (time.time() < (start_time + duration_of_signal)): # While time is less than duration of logged file
        print(adc.read_adc(0, gain=GAIN)*(5/2**16))

        if (time.time() > (start_time + (sampling_time * sampling_time_index))): # if time since last sample is more than the sampling time, take another sample
            dataVector1.append( adc.read_adc(0, gain=GAIN) ) # Perform analog to digital function, reading voltage from first sensor channel
            dataVector2.append( adc.read_adc(1, gain=GAIN) ) #  Perform analog to digital function, reading voltage from second sensor channel                     
            timeVector.append( time.time() - start_time )

            sampling_time_index += 1 # increment sampling_time_index to set awaited time for next data sample
            if ((sampling_time_index - 1) % 10 == 0):
                print(int(time.time() - start_time))

        elif (time.time() >= (start_time + sensing_delay_time) and time.time() <= (sensing_retract_time + start_time) and (adc.read_adc(0, gain=GAIN)*(5/2**16)) < extended_state):
            GPIO.output(linear_actuator_extend, GPIO.LOW) # Actuate linear actuator to extended position
            GPIO.output(linear_actuator_retract, GPIO.HIGH)# Energizing both control wires causes linear actuator to extend

        # If time is less than 10 seconds or greater than 50 seconds and linear actuator position sensor signal from DAQCplate indicates an extended state, retract the sensor
        elif ( ((time.time() < (sensing_delay_time + start_time)) or (time.time() > (sensing_retract_time + start_time)) ) and (adc.read_adc(0, gain=GAIN)*(5/2**16)) > retracted_state):
            GPIO.output(linear_actuator_retract, GPIO.LOW) # Retract linear actuator to initial position. Energizing only the linear_actuator_unlock_retract wire causes the lineaer actuator to retract
            GPIO.output(linear_actuator_extend, GPIO.HIGH)
        else:
            GPIO.output(linear_actuator_retract, GPIO.LOW)
            GPIO.output(linear_actuator_extend, GPIO.LOW)


    return dataVector1, dataVector2, timeVector

def intakeSample():
    GPIO.output(pump_pin, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(pump_pin, GPIO.LOW)



##intakeSample()
dataVector1, dataVector2, timeVector = exposeAndCollectData()

GPIO.cleanup()




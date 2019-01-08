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
from sklearn.neighbors import NearestNeighbors, KNeighborsClassifier
import pywt
from sklearn import preprocessing
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure


matplotlib.use("TkAgg")

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

## Global variable that will be used for starting and stopping the "getSample" action
continueTest = False
# Variable Declarations
sensor_input_channel_1 = 2 # Pin on ADC used to read analog signal from first sensor in dual channel sensor
sensor_input_channel_2 = 1 # Pin on ADC used to read analog signal from second sensor in dual channel sensor
linear_actuator_position_channel = 0 # Pin on ADC used to read analog signal from linear actuator internal position sensor

pumping_time = 20 # time allowed for vacuum pump to draw sample air
flow_stabilization_time = 2 # time allowed for air to settle after vacuum pump is shut off
sensing_delay_time = 9 # time delay after beginning data acquisition till when the sensor is exposed to sample
sensing_retract_time = 50 # time allowed before sensor is retracted, no longer exposed to sample
duration_of_signal = 200 # time allowed for data acquisition per test run
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
GPIO.setup(vacuum_pump, GPIO.OUT) # Specifies vacuum_pump pin as an output
GPIO.setup(linear_actuator_extend, GPIO.OUT) # Specifies linear_actuator_extend pin as an output
GPIO.setup(linear_actuator_unlock_retract, GPIO.OUT) # Specifies linear_actuator_unlock_retract pin as an output

# Initial state for outputs:
GPIO.output(vacuum_pump, GPIO.LOW)
GPIO.output(linear_actuator_extend, GPIO.LOW)
GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)

## This function creates folders by year, month and day
def createFolders(year, month, day):
    ##  Get the path for the folders by year, month and day
    year_path = '/home/pi/Documents/Tests/' + str(year)
    year_folder = Path(year_path)
    month_path = '/home/pi/Documents/Tests/' + str(year) + '/' + str(month)
    month_folder = Path(month_path)
    day_path = '/home/pi/Documents/Tests/' + str(year) + '/' + str(month) + '/' + str(day)
    day_folder = Path(day_path)
    ##  Start creating the folders, when the var complete == True, all the folders have been created
    complete = False
    while complete == False:
        if year_folder.is_dir():
            if month_folder.is_dir():
                if day_folder.is_dir():
                    complete = True
                else:
                    try:
                        print(day_path)
                        original_mask = os.umask(0x0000)
##                        desired_permission = 0777
                        os.makedirs(day_path, mode=0x0777)
                        complete = True
                    finally:
                        os.umask(original_mask)
            else:
                os.makedirs(month_path)
        else:
            os.makedirs(year_path)

def DW_transform(X_train, X_test):

	coeffs_train = pywt.wavedec(X_train, 'db6', level = 4)
	coeffs_test = pywt.wavedec(X_test, 'db6', level = 4)

	X_train_enc = coeffs_train[0]
	X_test_enc = coeffs_test[0]

	return X_train_enc, X_test_enc

def data_representation( X_train, X_test):

	### Z normalize each curve
	for i in range(X_train.shape[0]):
		mean = np.mean(X_train[i,:])
		stdev = np.std(  X_train[i,:] )
		X_train[i,:] = ( X_train[i,:] - mean ) / stdev

	for i in range(X_test.shape[0]):
		mean = np.mean(X_test[i,:])
		stdev = np.std(  X_test[i,:] )			
		X_test[i,:] = ( X_test[i,:] - mean ) / stdev

	### DWT representation
	X_train_enc, X_test_enc = DW_transform(X_train, X_test)


	return X_train_enc, X_test_enc

def featureProcessing(train, test):
	scaler = preprocessing.StandardScaler().fit(train)
	train = scaler.transform(train)
	test = scaler.transform(test)
	
	return train, test
            
## This function gets the current time for the time stamp of the txt file and for the folder location
def currentTime():
    current_time = datetime.datetime.now()
    year = current_time.year
    month = current_time.month
    day = current_time.day
    createFolders(year, month, day)
    hour = current_time.hour
    minute = current_time.minute
    second = current_time.second
    fileName = str(year) + '-' + str(month) + '-' + str(day) + ' ' + str(hour) + ':' + str(minute) + ':' + str(second)
    path = '/home/pi/Documents/Tests/' + str(year) + '/' + str(month) + '/' + str(day) + '/' + str(fileName) + '.txt'
    return path

## This function asks the user if they want to do another test, if not go back to the main menu
def newTest():
    result = messagebox.askquestion("New Test", "Do you want to do another test?")
    if result == 'yes':
        getSample()
    else:
        sys.exit()
## This function changes the flobal boolean variabel to false to stop the test        
def stopTest():
    global continueTest
    continueTest = False
    loadingScreen.destroy()
    getData.config(state="normal")
    #if you press stop, turn everything off, and purge?
    GPIO.output(vacuum_pump, GPIO.LOW)
##    while adc.read_adc(linear_actuator_position_channel,gain=GAIN) > retracted_state:
##        GPIO.output(linear_actuator_unlock_retract, GPIO.HIGH)
    GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)
    getData.config(state="normal")

def closePlotScreen():
	plotScreen.destroy()

#This function does all the gpio operations to obtain the sample
def getSample():
## Global variables
    global continueTest
    global loadingScreen
    global stopCounter
## Always make sure this is true at this point
    continueTest = True
## Loading screen code for the GUI
    getData.config(state="disabled")  ##  Disable the getData button, so that only one data acquisition can occur at the same time
    loadingScreen = tk.Toplevel(root)
    loadingScreen.geometry('300x200')
    tk.Label(loadingScreen, text="Recieving Data", width="40", height="5", font=(16)).pack()
    pb = ttk.Progressbar(loadingScreen, length=200, mode='determinate')
    pb.pack()
    pb.start(25)
    stop = tk.Button(loadingScreen, text="Stop Data Collection", command=stopTest, font=(16))
    stop.pack()
##  Run vacuum pump for duration of pumping_time to pull sampling air into sensing chamber
    print((adc.read_adc(sensor_input_channel_1,gain=GAIN)/pow(2, 15))*6.144)
##    time.sleep(3)
    print("Turn pump on")
    GPIO.output(vacuum_pump, GPIO.HIGH)
    pumping_time_counter = 0
    stopCounter = 0
##    Sleep second by second, the while loop makes sure to check if the user pressed stop every time its executed
    while (continueTest == True) and (pumping_time_counter < pumping_time):
        time.sleep(1)
        pumping_time_counter = pumping_time_counter + 1
## If we exit the while loop, check if it because time is over or because continueTest == False, if it is false go to newTest
    if continueTest == False and stopCounter == 0:
        stopCounter += 1
        print("test stopped 1")
        newTest()       
    print("Turn pump off")    
    GPIO.output(vacuum_pump, GPIO.LOW)
    # Wait for duration of flow_stabilization_time
    flow_stabilization_time_counter = 0
    print("Stabilization Time")
##    Sleep second by second, the while loop makes sure to check if the user pressed stop eveery time its executed
    while (continueTest == True) and (flow_stabilization_time_counter < flow_stabilization_time):
        time.sleep(1)
        flow_stabilization_time_counter = flow_stabilization_time_counter + 1
## If we exit the while loop, check if it because time is over or because continueTest == False, if it is false go to newTest
    if continueTest == False and stopCounter == 0:
        stopCounter += 1
        print("test stopped 2")
        newTest()  

    # Begin data collection
    dataVector1, dataVector2, timeVector = exposeAndCollectData()
    combinedVector = np.column_stack((timeVector, dataVector1, dataVector2))

    # This section of code is used for generating the output file name. The file name will contain date/time of test, as well as concentration values present during test
    current_time = datetime.datetime.now()
    year = current_time.year
    month = current_time.month
    day = current_time.day
    createFolders(year, month, day)
    hour = current_time.hour
    minute = current_time.minute
    fileName = str(year) + '-' + str(month) + '-' + str(day) + '_' + str(hour) + ':' + str(minute) + '.csv'
    np.savetxt(r'/home/pi/Documents/Tests/' + str(year) + '/' + str(month) + '/' + str(day) + '/' + str(fileName),
               combinedVector, fmt='%.10f', delimiter=',')

    # Perform on-line prediction based on 1NN classifier
    filepath = '/home/pi/Documents/'
    x_train = np.transpose( genfromtxt(filepath + 'train.csv', delimiter=',') )
    x_test = dataVector1
    Y_train = genfromtxt(filepath + 'targets_train_binary.csv', delimiter=',')

    # Downsampling parameters
    desiredTimeBetweenSamples = 1
    timeBetweenSamples = 0.1
    samplingRatio = math.floor(desiredTimeBetweenSamples/timeBetweenSamples)

    ### Moving average filter (filters noise)
    samples = 5
    smoothedData = np.zeros((x_test.shape[0],x_test.shape[1]))

    for j in range(samples, x_test.shape[0]-samples):
            sum = 0

            for k in range(-1*samples, samples+1):
                    sum = sum + x_test[j+k][0]

            smoothedData[j] = sum/(2*samples+1)

    for j in range(smoothedData.shape[0]):
                    if smoothedData[j][0] == 0:
                            smoothedData[j][0] = x_test[j][0]

    # Downsample
    downsampledData = np.zeros((1,1))
    for j in range(smoothedData.shape[0]):
            if (j%samplingRatio == 0):
                    if(j == 0):
                                downsampledData[0][0] = np.array([[smoothedData[j,0]]])
                    else:
                            downsampledData = np.vstack((downsampledData,np.array([[smoothedData[j,0]]])))

    # Convert from voltage to fractional change in conductance
    for j in range(downsampledData.shape[0]):
            V = downsampledData[j][0]
            downsampledData[j][0] = V/(R*(V0-V))
    x_test = downsampledData

    post_p = True
    x_train, x_test = data_representation( x_train, x_test,  prep = 4, rep = 'DWT' )
    if post_p == True:
            x_train, x_test = featureProcessing(x_train, x_test)

    ### Fit 1NN classifier based on previously collected data
    clf = KNeighborsClassifier(n_neighbors = 1, algorithm = 'brute')
    clf.fit(x_train, Y_train)

    ### Predict label of new test
    y_pred = clf.predict(x_test)
    if y_pred == 0:
            print("Sample predicted as being methane")
    elif y_pred == 1:
            print("Sample predicted as being natural gas")
    else:
            print("Classifier error, please check")
    
    if continueTest == False and stopCounter == 0:
        stopCounter += 1
        print("test stopped 3")
        newTest()

    ### plot new test
    plotScreen = tk.Toplevel(root)
    plotScreen.geometry('300x200')
    tk.Label(plotScreen, text="Data plot", width="40", height="5", font=(16)).pack()
    f = Figure(figsize=(5,5), dpi=100)
    f.plot(x_test)
    f.show()

    closeButton = tk.Button(plotScreen, text="Close", command=closePlotScreen, font=(16))
        
    stopTest()
## This function calculates the vltage value read by the ADC  
def ADC_linear_actuator():
    conversion_value = (adc.read_adc(linear_actuator_position_channel,gain=GAIN)/pow(2, 15))*6.144
    return conversion_value

##This funciton collects the data
def exposeAndCollectData():
    global stopCounter
    start_time = time.time()  # capture the time at which the test began. All time values can use start_time as a reference
    dataVector1 = []  # data values to be returned from sensor 1
    dataVector2 = []  # data values to be returned from sensor 2
    timeVector = []  # time values associated with data values
    sampling_time_index = 1  # sampling_time_index is used to ensure that sampling takes place every interval of sampling_time, without drifting.

    print("Starting data capture")

    while (time.time() < (start_time + duration_of_signal)) and (continueTest == True):  # While time is less than duration of logged file
        if (time.time() > (start_time + (
                sampling_time * sampling_time_index)) and (continueTest == True)):  # if time since last sample is more than the sampling time, take another sample
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
                sensing_retract_time + start_time) and ADC_linear_actuator() < extended_state) and (continueTest == True):
##            print("extend actuator")
            GPIO.output(linear_actuator_extend, GPIO.HIGH)  # Actuate linear actuator to extended position
            GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)  # Energizing both control wires causes linear actuator to extend

        # If time is less than 10 seconds or greater than 50 seconds and linear actuator position sensor signal from the ADC indicates an extended state, retract the sensor
        elif (((time.time() < (sensing_delay_time + start_time)) or (
                time.time() > (sensing_retract_time + start_time))) and ADC_linear_actuator() > retracted_state) and (continueTest == True):
##            print("retract actuator")
            GPIO.output(linear_actuator_unlock_retract,GPIO.HIGH)  # Retract linear actuator to initial position. Energizing only the linear_actuator_unlock_retract wire causes the linear actuator to retract
            GPIO.output(linear_actuator_extend, GPIO.LOW)
        # Otherwise, keep outputs off
        else:
            GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)
            GPIO.output(linear_actuator_extend, GPIO.LOW)
            
    return dataVector1, dataVector2, timeVector

## This function starts a new thread get sample, and the main thread to checks if the stop button has been pressed
def startTest():
    global continueTest
    continueTest = True
    _thread.start_new_thread(getSample, ())

##GUI - Main Menu
try:
    root = tk.Tk()
    root.title("Hetek Data Analysis")
    mainText = tk.Label(root, text="Please select an option, \npress STOP to interrupt data acquisition:", width="60",
                        height="10", font=(20))
    mainText.pack()
    frame = tk.Frame(root)
    frame.pack()
    button = tk.Button(frame, text="QUIT", fg="red", command=quit, font=(18))
    button.pack(side=tk.LEFT)
    getData = tk.Button(frame, text="Get data", command=startTest, font=(18))
    getData.pack(side=tk.LEFT)
    root.mainloop()
finally:
    GPIO.cleanup()

# Imports
import RPi.GPIO as GPIO
import time

#---------------------------------------------------------------------#

pump_pin = 40


# Pin Setup:
GPIO.setmode(GPIO.BOARD)
GPIO.cleanup()

GPIO.setmode(GPIO.BOARD)
GPIO.setup(pump_pin, GPIO.OUT)


# Initial state for outputs:
GPIO.output(pump_pin, GPIO.HIGH)
time.sleep(30)
GPIO.cleanup()
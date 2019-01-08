import RPi.GPIO as GPIO
import time
import Adafruit_ADS1x15
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 2 / 3
linear_actuator_position_channel = 0 # Pin on ADC used to read analog signal from linear actuator internal position sensor

def ADC_linear_actuator():
    conversion_value = (adc.read_adc(linear_actuator_position_channel,gain=GAIN)/pow(2, 15))*6.144
    return conversion_value

linear_actuator_extend = 27 # Broadcom pin 5 (P1 pin 13)
linear_actuator_unlock_retract = 22 # Broadcom pin 12 (P1 pin 15)

# Pin Setup:
GPIO.setmode(GPIO.BCM)    # There are two options for this, but just use the board one for now. Don't worry much about it, we can check the definitions when I get back
GPIO.setup(linear_actuator_extend, GPIO.OUT) # Specifies linear_actuator_extend pin as an output
GPIO.setup(linear_actuator_unlock_retract, GPIO.OUT) # Specifies linear_actuator_unlock_retract pin as an output

print(ADC_linear_actuator())
GPIO.output(linear_actuator_extend, GPIO.HIGH)
GPIO.output(linear_actuator_unlock_retract, GPIO.LOW)
time.sleep(2)
print(ADC_linear_actuator())
GPIO.cleanup()
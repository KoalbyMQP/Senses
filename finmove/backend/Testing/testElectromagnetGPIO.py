import RPi.GPIO as GPIO
import time

electromagnetPin = 14

GPIO.setmode(GPIO.BCM)
GPIO.setup(electromagnetPin, GPIO.OUT)
GPIO.output(electromagnetPin, GPIO.HIGH)

while True:
    input("Press anything to toggle electromagnet, CTRL+C to quit")
    GPIO.output(electromagnetPin, GPIO.LOW)
    input("Press anything to toggle electromagnet, CTRL+C to quit")
    GPIO.output(electromagnetPin, GPIO.HIGH)
    
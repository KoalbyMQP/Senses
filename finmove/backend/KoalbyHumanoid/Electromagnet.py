on_raspi = True

try:
    import RPi.GPIO as GPIO
except:
    print("Not on Raspberry Pi, cannot initialize GPIO. If on Raspberry Pi, ensure RPi.GPIO is installed.")
    on_raspi = False
    
import signal
from enum import Enum

ELECTROMAGNET_GPIO_PIN = 14

class ElectromagnetState(Enum):
    OFF = 0
    ON = 1

class Electromagnet():
    def __init__(self, pin=ELECTROMAGNET_GPIO_PIN):
        self.pin = pin
        if(on_raspi):
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
        self.state = ElectromagnetState.OFF
        self.turnOff() # off by default

        # Turns off upon ctrl+c
        signal.signal(signal.SIGINT, self.onExit)
    
    def onExit(self, sig, frame):
        self.turnOff()
        exit(0)
        
    def turnOn(self):
        if(on_raspi):
            GPIO.output(self.pin, GPIO.LOW)
        self.state = ElectromagnetState.ON
        
    def turnOff(self):
        if(on_raspi):
            GPIO.output(self.pin, GPIO.HIGH) 
        self.state = ElectromagnetState.OFF
        
    def toggle(self):
        if self.state == ElectromagnetState.OFF:
            self.turnOn()
        else:
            self.turnOff()
        
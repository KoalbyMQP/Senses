import sys
sys.path.append(".")
from backend.KoalbyHumanoid.Electromagnet import *

e = Electromagnet()

while True:
    input("Press enter to toggle electromagnet, CTRL+C to quit")
    e.toggle()
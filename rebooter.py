import time
import sys
import signal
import os

if len(sys.argv) != 3:
    exit()

delay = int(sys.argv[1])
pid = int(sys.argv[1])
time.sleep(delay)

# os.kill(pid, signal.SIGTERM)
os.system('python main.py --rebooted')

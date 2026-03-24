import time
import RPi.GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

#using physical pin 11 to blink an LED
GPIO.setmode(GPIO.BOARD)
chan_list = [11]
GPIO.setup(chan_list, GPIO.OUT)

# Hardware SPI configuration:
SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

# by taking readings and printing them out, find
# appropriate threshold levels and set them 
# accordingly. Then, use them to determine
# when it is light or dark, quiet or loud.
lux_treshold=200  # change this value
sound_treshold=600 # change this value


while True: 

  #Following commands control the state of the output
  #GPIO.output(pin, GPIO.HIGH)
  #GPIO.output(pin, GPIO.LOW)

  # get reading from adc 
  # mcp.read_adc(adc_channel)

  for i in range(5):
    GPIO.output(11, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(11, GPIO.LOW)
    time.sleep(0.5)

  for i in range(50):
    light_val = mcp.read_adc(0)
    if light_val > lux_treshold:
      state = "bright"
    else:
      state = "dark"
    print("Light:", light_val, state)
    time.sleep(0.1)

  for i in range(4):
    GPIO.output(11, GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(11, GPIO.LOW)
    time.sleep(0.2)

  for i in range(50):
    sound_val = mcp.read_adc(1)
    print("Sound:", sound_val)
    if sound_val > sound_treshold:
      GPIO.output(11, GPIO.HIGH)
      time.sleep(0.1)
      GPIO.output(11, GPIO.LOW)
    else:
      time.sleep(0.1)
# Lab 06 Writeup

## Abhigya Goel, (No Partner Found Unfortunately)

### 4.1

```bash
git clone git@github.com:AbhigyaGoel/ee250.git
cd ee250
touch my_second_file.py
echo 'print("Hello World")' > my_second_file.py
git add my_second_file.py
git commit -m "added my_second_file.py"
git push origin main
```

### 4.2

The workflow was to write my code on my laptop in VScode, push to Github, then SSH into the Pi and pull those pushes to test on the hardware. For any tweaks I just did it on the Pi with nano to
avoid having to push and pull again. Going forwards, I need to get better with vi since most of the debugging was on the Pi and it would speed up iterating.

### 4.3

Even without the straight up 200 ms sleep, there is still a delay because the ultrasonicRead() function in the grovepi library internally calls time.sleep(0.06), which is a 60 ms pause. This wait is needed so that the ATmega328P has enough time to actually fire the ultrasonic pulse, then listen for the echo, then compute the round-trip time, and then make the result available over the bus. The communication protocol between the Raspberry Pi and the ATmega328P on the GrovePi is I2C. The Pi works as the master on the I2C bus and sends a command byte to request an ultrasonic reading, and then reads the result bytes back from the ATmega after the delay.

### 4.4

The rotary angle sensor gives a smooth analog voltage that goes from 0-5V as the knob turns. The ATmega328P on the GrovePi board has a 10-bit ADC that samples this voltage, subsequently quantizing it into one of 1024 discrete steps (0 through 1023). So 0V maps to 0, 5V maps to 1023, and any voltage in between maps proportionally. The Raspberry Pi lacks an ADC, and so its GPIO pins are just digital and can only differentiate between high and low logic. It has no way to measure any intermediate voltage on its own, which is why the ATmega handles that conversion and sends the digital result to the Pi over I2C.

### 4.5

If the LCD runs without errors but stays blank, the first thing to check is whether the Pi can even see the LCD on the I2C bus: sudo i2cdetect -y 1

The LCD should show up at addresses 0x3e (this is the text controller) and 0x62 (this is the RGB backlight).
If those addresses are missing, the cable or the LCD module itself is most likely the problem.

Next, confirm the GrovePi firmware is responding: cd ~/Dexter/GrovePi/Software/Python && python grove_firmware_version_check.py

A response like `1.4.0` means firmware is fine, but if it returns `255.255.255`, the firmware flash most likely failed and the setup steps need to be re-run. Swapping the Grove cable is also a valid check since those 4-pin connectors might be loose.

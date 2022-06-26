# xsens_driver
A python implementation of a standalone Xsens driver that supports communication with the MTi devices using the Xsense Xbus protocol.
## Xbus reconstructor
Contains logic to reconstruct the xbus messages correctly by parsing the packet delimiter & packet length. This is necessary since the xbus packets can be split up over different serial reads.
This logic is tested in the `xbus_reconstructor_tests.py`
You can run the tests using `python3 -m unittest tests.xbus_reconstructor_tests`

## Running this repo
Using `python3 raw_xsens_comms.py` a connection can be set up with the MTi device. You can setup the serial port by changing the `self.serial_port = '/dev/ttyUSB0'` variable (it should be a COM port if you are using windows). This script will configure the MTi device to send out the following information:
```
            50 42 00 0A -> Position at 10Hz
            20 30 00 0A -> Rotation in Euler angles at 10Hz
            40 30 00 64 -> Free acceleration at 100Hz
            80 20 00 0A -> Rate of turn at 10Hz
            D0 12 00 0A -> Velocity at 10 Hz
            E0 20 FF FF -> Status word whenever available
```
The roll & free accelerations values will be printed out in the console.
Support for more messages can easily be added in the `xbus_reconstructor.py` in the `__parse_mtdata2_message` method. Pull requests are welcome! 
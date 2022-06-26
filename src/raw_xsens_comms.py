import serial
import logging
import threading
import queue
from xbus_reconstructor import XbusReconstructor

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s')  

class ImuReader:
    def __init__(self):
        self.serial_port = '/dev/ttyUSB0'
        self.baudrate = 115200
        self.send_queue = queue.Queue()
        self.go_to_config_mode()
        self.set_output_conf()
        self.packet_length = None
        self.xbus_reconstructor = XbusReconstructor()
        self.go_to_measurement_mode()
        d = threading.Thread(name='daemon', target=self.connect)
        #d.setDaemon(True)
        d.start()  
    
    def connect(self):
        with serial.Serial(self.serial_port, self.baudrate, timeout=5) as ser:
            while True:
                data = ser.read_until(b'\xfa')
                #data = ser.read(100)
                #logging.info(f'read data: {data}')
                parse_xbus_data_list = self.xbus_reconstructor.parse_xbus_data(data)
                logging.info(f'parsed: {parse_xbus_data_list}')
                #Just take one for now
                if len(parse_xbus_data_list) > 0:
                    parsed_xbus_data = parse_xbus_data_list[0]
                    if len(parsed_xbus_data) > 0:
                        if 'roll' in parsed_xbus_data:
                            logging.info(f"""
                                roll: {parsed_xbus_data['roll']},
                                pitch: {parsed_xbus_data['pitch']},
                                yaw' {parsed_xbus_data['yaw']}
                            """)
                        
                        if 'freeAccX' in parsed_xbus_data:
                            logging.info(f"""
                                Ax: {parsed_xbus_data['freeAccX']},
                                Ay: {parsed_xbus_data['freeAccY']},
                                Az: {parsed_xbus_data['freeAccZ']}
                            """)
                while not self.send_queue.empty():
                    send_data = self.send_queue.get()
                    logging.info(f'sending to device: {send_data}')
                    ser.write(send_data)

    def go_to_measurement_mode(self):
        self.send_queue.put(bytes.fromhex('FAFF1000F1'))

    def go_to_config_mode(self):
        self.send_queue.put(bytes.fromhex('FAFF3000D1'))

    
    def set_output_conf(self):
        """Configures the Imu to the following:
        Output:
            50 42 00 0A -> Position at 10Hz
            20 30 00 0A -> Rotation in Euler angles at 10Hz
            40 30 00 64 -> Free acceleration at 100Hz
            80 20 00 0A -> Rate of turn at 10Hz
            D0 12 00 0A -> Velocity at 10 Hz
            E0 20 FF FF -> Status word whenever available
        """
        self.send_queue.put(bytes.fromhex('FAFFC0185042000A2030000A403000648020000AD012000AE020FFFFCB'))



if __name__ == '__main__':
    imu_reader = ImuReader()


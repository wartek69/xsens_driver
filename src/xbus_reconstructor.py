import sys
import logging
import struct
import numpy as np
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s')

class XbusReconstructor:
    def __init__(self):
        self.total_payload_length = None
        #incomplete_msg_buffer is used to bring over bytes from an incomplete message to the next iteration
        self.incomplete_msg_buffer = b''
        self.did_sync_with_stream = False

        #prebuffer is used to make sure that we atleast have 4 bytes to read out the total length
        self.prebuffer = b''

    def calculate_checksum(self, msg_bytes_without_cs):
        """Calculates checksum for xbus message

        Args:
            msg_bytes_without_cs (byte_string): msg bytes without the checksum

        Returns:
            np.uint8: checksum of provided msg bytes
        """
        checksum = 0
        for idx, msg_byte in enumerate(msg_bytes_without_cs):
            if idx == 0:
                #skip preamble bytes
                continue
            checksum -= msg_byte
        return np.uint8(checksum)


    def __find_start_of_xbus_data(self, msg_bytes):
        """Removes all prepended bytes that could arrive on first read.

        Args:
            msg_bytes (byte_array): Byte array containing received bytes
        Returns:
            byte_array: Byte array with the prepended bytes stripped from it
        """

        if not self.did_sync_with_stream and msg_bytes[0] != 0xfa:
            #Find the first full message
            for idx, msg_byte in enumerate(msg_bytes):
                if msg_byte == 0xfa:
                    #Start of message found
                    logging.warning('Had to cut out part of message since it did not start with preamble!')
                    return msg_bytes[idx:]
        return msg_bytes

    def _reconstruct_xbus_data(self, msg_bytes):
        if msg_bytes == b'':
            logging.warning('Received an empty message!')
            return []
        xbus_delimited_message = self.__find_start_of_xbus_data(msg_bytes)
        self.prebuffer += xbus_delimited_message
        self.did_sync_with_stream = True

        if len(self.prebuffer) < 4:
            print('Message is too small, cannot get the length! Buffering for now')
            return []

        reconstructed_messages = []
        while len(self.prebuffer) >= 4:
            if self.incomplete_msg_buffer == b'':
                self.total_payload_length = int(self.prebuffer[3])
                #Total payload length also needs to include preamble, BID, MID, LEN and checksum bytes
                self.total_payload_length += 5

            #We do not support extended packet lenghts yet
            assert self.total_payload_length < 255

            payload_bytes_left = self.total_payload_length - len(self.incomplete_msg_buffer)
            partial_payload_bytes = self.incomplete_msg_buffer + self.prebuffer[:payload_bytes_left]
            self.prebuffer = self.prebuffer[payload_bytes_left:]


            if len(partial_payload_bytes) == self.total_payload_length:
                assert partial_payload_bytes[-1] == self.calculate_checksum(partial_payload_bytes[:-1])
                reconstructed_messages.append(partial_payload_bytes)
                self.incomplete_msg_buffer = b''
            elif len(partial_payload_bytes) < self.total_payload_length:
                self.incomplete_msg_buffer = partial_payload_bytes
            elif len(partial_payload_bytes) > self.total_payload_length:
                sys.exit('ERROR: Cannot have a partial payload bigger than amount of payload bytes, check your code!')

        return reconstructed_messages

    def parse_xbus_data(self, msg_bytes):
        parsed_msgs = []
        reconstructed_messages = self._reconstruct_xbus_data(msg_bytes)
        for reconstructed_msg in reconstructed_messages:
            message_identifier = reconstructed_msg[2]
            if message_identifier == 0x36:
                parsed_msgs.append(self.__parse_mtdata2_message(reconstructed_msg))
        return parsed_msgs



    def __parse_mtdata2_message(self, reconstruced_msg):
        parsed_data_dict = {}
        data_part = reconstruced_msg[4:-1]
        bytes_offset = 0

        while bytes_offset < len(data_part):
            #2bytes used for data id
            data_id = data_part[bytes_offset + 0: bytes_offset + 2]
            #1byte used for data len
            data_len = int.from_bytes(data_part[bytes_offset + 2:bytes_offset + 3], 'big')

            packet_data = data_part[bytes_offset + 3: bytes_offset + 3 + data_len]

            if data_id == bytes.fromhex('2030'):
                #4bytes each
                parsed_data_dict['roll'] = struct.unpack('>f', packet_data[:4])
                parsed_data_dict['pitch'] = struct.unpack('>f', packet_data[4:8])
                parsed_data_dict['yaw'] = struct.unpack('>f', packet_data[8:])
            elif data_id == bytes.fromhex('4030'):
                #free accelerations
                parsed_data_dict['freeAccX'] = struct.unpack('>f', packet_data[:4])
                parsed_data_dict['freeAccY'] = struct.unpack('>f', packet_data[4:8])
                parsed_data_dict['freeAccZ'] = struct.unpack('>f', packet_data[8:])


            bytes_offset += data_len + 3 # 2bytes used for data id and 1 byte for size field

        return parsed_data_dict


#!/usr/bin/python3
# coding=UTF-8


def crc16(crc, data_byte):
    crc ^= data_byte
    for i in range(8):
        crc = crc >> 1 ^ 0xA001 * (crc & 1)
    return crc


def crc16_test():
    data = b'123456789'
    crc = 0xFFFF
    for data_byte in data:
        crc = crc16(crc, data_byte)
    print(hex(crc + 0x10000)[-4:])
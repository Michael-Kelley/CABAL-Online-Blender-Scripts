#--------------------------------#
# Helper functions for reading   #
# from and writing to binary     #
# files.                         #
#--------------------------------#
# Author: Michael K.             #
#--------------------------------#


import struct


#----------------#


def read_byte(file):
	return struct.unpack('<B', file.read(1))[0]

def read_sbyte(file):
	return struct.unpack('<b', file.read(1))[0]

def read_ushort(file):
	return struct.unpack('<H', file.read(2))[0]

def read_short(file):
	return struct.unpack('<h', file.read(2))[0]

def read_uint(file):
	return struct.unpack('<I', file.read(4))[0]

def read_int(file):
	return struct.unpack('<i', file.read(4))[0]

def read_float(file):
	return struct.unpack('<f', file.read(4))[0]

def read_bytes(file, count):
	return struct.unpack('<%dB'%count, file.read(count))

def read_shorts(file, count):
	return struct.unpack('<%dh'%count, file.read(2*count))

def read_ints(file, count):
	return struct.unpack('<%di'%count, file.read(4*count))

def read_floats(file, count):
	return struct.unpack('<%df'%count, file.read(4*count))
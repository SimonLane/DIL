# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 14:49:34 2024
USB 3103 - Analog and Digital Write minimal working example
@author: sil1r12
"""

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType, DigitalIODirection
 


Dchannel = 2
Achannel = 0

# get board
board_num = 0
dev_id_list = []
ul.ignore_instacal()
device = ul.get_daq_device_inventory(InterfaceType.ANY)[0]


ul.create_daq_device(board_num, device)
print('board number: ', board_num)

daq_dev_info = DaqDeviceInfo(board_num)
ao_info = daq_dev_info.get_ao_info()
ao_range = ao_info.supported_ranges[0]

dio_info = daq_dev_info.get_dio_info()
print('number of digital ports: ', dio_info.num_ports)

port = next((port for port in dio_info.port_info if port.supports_output),None)

# set digital ports as outputs
ul.d_config_port(0,port.type, DigitalIODirection.OUT)

ul.d_bit_out(board_num,port.type,Dchannel,0)  # set Dchannel high

ul.a_out(board_num,Achannel,ao_info.supported_ranges[0], 65000)  #set analog channel

ul.release_daq_device(board_num)











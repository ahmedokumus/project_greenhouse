import snap7
from snap7.util import set_string

# PLC'ye bağlan
plc = snap7.client.Client()
plc.connect("192.168.0.1", 0, 1)  # PLC IP ve Rack-Slot bilgisi

# DB1'de belirlenen offset'e string yaz
db_number = 1
start_offset = 0  # String'in başlayacağı adres
size = 100  # Maksimum string uzunluğu

data = bytearray(size)
set_string(data, 0, "HELLO", size)  # String'i uygun formatta yerleştir

plc.db_write(1, 0, data)  # PLC'ye yaz

plc.disconnect()

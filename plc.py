import snap7
from snap7.util import get_real, set_bool


def connect_to_plc(ip: str = "192.168.0.1", rack: int = 0, slot: int = 1):
    client = snap7.client.Client()
    client.connect(ip, rack, slot)
    return client


def read_md_float(plc, start, area: any = snap7.type.Areas.MK):
    if (area == snap7.type.Areas.MK):
        data = plc.read_area(area, 0, start, 4)
        return get_real(data, 0)
    else:
        print("Bu işlem sadece MK alanı için geçerlidir.")
    plc.disconnect()


def write_bit(plc, byte_index, bit_index, value, area: any = snap7.type.Areas.PA):
    if (area == snap7.type.Areas.PA):
        data = plc.read_area(area, 0, byte_index, 1)
        set_bool(data, 0, bit_index, value)
        plc.write_area(area, 0, byte_index, data)
        print(f"Q{byte_index}.{bit_index} çıkışı {value} yapıldı.")
    else:
        print("Bu işlem sadece PA alanı için geçerlidir.")
    plc.disconnect()


if __name__ == "__main__":
    plc = connect_to_plc()

    float_value = read_md_float(plc, 1)
    print(f"Okunan Float Değer: {float_value}")

    write_bit(plc, byte_index=0, bit_index=1, value=0)

    plc.disconnect()
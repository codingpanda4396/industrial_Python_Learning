import snap7
from snap7.util import *

class PLC_client:
    """
    负责与S7-PLC模拟器建立连接和进行基本的数据读写操作
    """
    def __init__(self, ip: str, rack: int = 0, slot: int = 1):
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.plc = snap7.client.Client()
        self.connected = False

    def connect(self) -> bool:
        """连接到PLC模拟器"""
        try:
            self.plc.connect(self.ip, self.rack, self.slot)
            self.connected = self.plc.get_connected()
            print("连接PLC成功")
            return self.connected
        except Exception as e:
            print(f"连接PLC时发生异常: {e}")
            return False

    def disconnect(self):
        """断开与PLC模拟器的连接"""
        if self.connected:
            self.plc.disconnect()
            self.connected = False
            print("已断开与PLC的连接。")

    def read_bool(self, db_number: int, byte_index: int, bit_index: int) -> bool:
        """从DB块读取一个布尔值"""
        data = self.plc.db_read(db_number, byte_index, 1)
        return get_bool(data, 0, bit_index)

    def read_int(self, db_number: int, byte_index: int) -> int:
        """从DB块读取一个整数值"""
        data = self.plc.db_read(db_number, byte_index, 2)
        return get_int(data, 0)

    def read_real(self, db_number: int, byte_index: int) -> float:
        """从DB块读取一个实数值（浮点数）"""
        data = self.plc.db_read(db_number, byte_index, 4)
        return get_real(data, 0)

    def write_bool(self, db_number: int, byte_index: int, bit_index: int, value: bool):
        """向DB块写入一个布尔值"""
        data = self.plc.db_read(db_number, byte_index, 1)
        set_bool(data, 0, bit_index, value)
        self.plc.db_write(db_number, byte_index, data)

    def write_int(self, db_number: int, byte_index: int, value: int):
        """向DB块写入一个整数值"""
        data = bytearray(2)
        set_int(data, 0, value)
        self.plc.db_write(db_number, byte_index, data)
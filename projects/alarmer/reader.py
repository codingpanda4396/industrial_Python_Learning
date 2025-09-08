class plc_reader:
    """专门做读取操作"""
    def __init__(self,plc):
        self._plc= plc
    
    def read_sensor_data(self,db_num,offset,byte_len):
        """从指定的DB号读取多个字节的数据"""
        data = self._plc.db_read(db_num,offset,byte_len)#读取db_num号
        return data
    
from time import time
import snap7

class plc_connector:
    """用来获取plc连接"""
    def __init__(self, ip, rack=0, slot=1):
        self._ip = ip
        self._rack = rack
        self._slot = slot
        self._plc = None  # 将连接对象作为私有属性保护起来
        self._connect()  # 初始化时建立连接

    def _connect(self):
        """内部使用的连接方法，包含重试机制"""
        while True:
            try:
                client = snap7.client.Client()
                client.connect(self._ip,self._rack,self._slot)
                if client.get_connected:
                    print(f"成功连接到PLC IP: {self._ip}, Rack: {self._rack}, Slot: {self._slot}")
                    self._plc = client
                    break
                else:
                    print("连接失败，PLC未就绪。")
            except Exception as e:
                print(f"连接PLC时发生错误: {e}")
            print(f"{10}秒后重试...")
            time.sleep(10)  # 等待一段时间后重试

    @property
    def plc(self)-> snap7.client.Client:
        """获取plc连接对象"""
        if self._plc is None or not self._plc.get_connected():
            self._reconnect()
        return self._plc
    

    def _reconnect(self):
        """处理重连逻辑"""
        print("PLC连接已断开，尝试重新连接...")
        if self._plc is not None:
            try:
                self._plc.destroy()
            except Exception as e:
                print(f"清理旧连接时发生错误: {e}")
        self._plc = None
        self._connect()

    # def __del__(self):
    #     """析构函数，确保对象销毁时断开连接"""
    #     if self._plc is not None:
    #         try:
    #             self._plc.disconnect()
    #             self._plc.destroy()
    #             print("连接已断开并清理。")
    #         except Exception as e:
    #             print(f"断开连接时发生错误: {e}")



if __name__ == "__main__":
    ip="127.0.0.1"
    connector=plc_connector(ip)
    plc_client=connector.plc

    
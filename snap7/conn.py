import struct
from time import sleep
import snap7



def write_db1(plc_client):
    real_value1=439695
    data_to_write= struct.pack('>f', real_value1)#根据格式字符串把值打包为bytes对象

    plc_client.db_write(1,0,data_to_write)#1号DB 起始地址0 内容 
    print(f"已经写入Real值{data_to_write}到DB1.DBD0")

def read_db1(plc_client):
    data=plc_client.db_read(1,0,4)#1号DB 起始地址0 读取长度（4字节 ）
    real_value=snap7.util.get_real(data,0)
    return f"读取到的Real值{real_value}"



def main():
    plc=snap7.client.Client()

    ip_address = '127.0.0.1'  # 本地回环地址，连接本机运行的Server
    rack = 0
    slot = 1

    try:
        print("正在连接PLC...")
        plc.connect(ip_address,rack,slot)
        if plc.get_connected():
            print("成功连接到PLC Server")

            write_db1(plc)
            sleep(5)

            print(read_db1(plc))
        else:
            print("PlC连接失败")
    except Exception  as e:
        print(e)

    finally:
        plc.disconnect()
        plc.destroy()
        print("连接已断开")

if __name__ == "__main__":
    main()
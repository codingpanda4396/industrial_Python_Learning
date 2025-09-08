from conn import plc_connector
from reader import plc_reader

def main():
    ip = "127.0.0.1"
    plc_client = plc_connector(ip).plc
    reader= plc_reader(plc_client)
    data=reader.read_sensor_data(1,0,4)
    print(data.decode('utf-8'))

if __name__ ==  "__main__":
    main()


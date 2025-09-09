from plc_client import PLC_client
from logger  import DataLogger
from alarm import *
def main():
    ip="127.0.0.1"
    client= PLC_client(ip)
    client.connect()
    logger = DataLogger()

    monitor = AlarmMonitor(client,logger,poll_interval=3.0)

    # 温度高报警，上限50.0，死区2.0（滞环）
    high_temp_rule = AlarmRule("温度过高", 50.0, -273.15, 2.0, "温度超过50度触发报警")
    # 温度低报警，下限10.0，死区1.0
    low_temp_rule = AlarmRule("温度过低", 100.0, 10.0, 1.0, "温度低于10度触发报警")
    
    monitor.add_alarm_rule(high_temp_rule)
    monitor.add_alarm_rule(low_temp_rule)

    try:
        if monitor.start_monitoring():
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止监控")
    finally:
        monitor.stop_monitoring()
        client.disconnect()

    

if __name__ ==  "__main__":
    main()


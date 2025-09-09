import threading
import time
from typing import List, Optional
from logger import DataLogger



class AlarmRule:
    """报警规则"""
    def __init__(self,name: str, high_limit: float, low_limit: float, deadband: float = 0.0, description: str = ""):
        self.name = name
        self.high_limit = high_limit
        self.low_limit = low_limit
        self.deadband = deadband  # 报警死区，用于计算滞环
        self.high_recovery = high_limit - deadband  # 高报警恢复值
        self.low_recovery = low_limit + deadband   # 低报警恢复值
        self.description = description
        self.triggered = False  # 当前报警触发状态
    def alarm(self,value:float)->bool:
        """
        检查数值是否触发报警，应用滞环逻辑。
        返回True表示报警状态，False表示正常状态。
        """
        if not self.triggered:
            if value>self.high_limit or value<self.low_limit:
                self.triggered=True
                return True
        else:
            #已报警，检查是否恢复
            if value<=self.high_recovery and value>=self.low_recovery:
                self.triggered=False
                return False
            else:
                return True
class AlarmMonitor:
    def __init__(self, plc_client, data_logger: DataLogger, poll_interval: float = 5.0):
        self.plc_client = plc_client
        self.data_logger = data_logger
        self.poll_interval = poll_interval  # 轮询间隔（秒）
        self.alarm_rules: List[AlarmRule] = []
        self.is_monitoring = False#正在监视的标识
        self.monitor_thread: Optional[threading.Thread] = None       

    def add_alarm_rule(self,rule:AlarmRule):
        self.alarm_rules.append(rule)

    def start_monitoring(self):
        """启动监控线程"""
        if not self.plc_client:#未连接
            self.data_logger.log_message("错误：无法连接到PLC，监控启动失败。")
            return False

        self.is_monitoring = True#标记正在监听
        #另起一个线程
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.data_logger.log_message("报警监控已启动。")
        return True

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()

            self.data_logger.log_message("报警监控已停止。")
    def _monitoring_loop(self):
        """监控主循环，在独立线程中运行"""
        try:
            while self.is_monitoring:       
                # 1. 读取PLC数据 (示例地址，需根据你的PLC程序调整)
                try:
                    temperature = self.plc_client.read_real(1, 0)  # 假设温度值在DB1.DBD0
                    motor_running = self.plc_client.read_bool(1, 10, 0)  # 假设电机状态在DB1.DBX10.0
                    pressure = self.plc_client.read_int(1, 12)  # 假设压力值在DB1.DBW12[1](@ref)

                except Exception as e:
                    self.data_logger.log_message(f"读取PLC数据时发生错误: {e}")
                    time.sleep(self.poll_interval)
                    continue

                # 2. 检查报警规则
                current_alarms = []
                for rule in self.alarm_rules:
                    if rule.alarm(temperature):  # 这里以温度为例
                        #触发警报：加入警报list
                        current_alarms.append(rule.name)

                # 3. 根据报警状态执行控制逻辑 (示例)
                if current_alarms:
                    # 触发报警输出，例如点亮报警灯 (假设Q0.0对应DB2.DBX0.0)
                    try:
                        self.plc_client.write_bool(2, 0, 0, True)
                    except Exception as e:
                        self.data_logger.log_message(f"写入PLC报警输出时发生错误: {e}")
                    alarm_msg = f"报警触发！规则: {', '.join(current_alarms)} | 温度: {temperature:.2f}, 压力: {pressure}, 电机运行: {motor_running}"
                    self.data_logger.log_message(alarm_msg)
                else:
                    # 报警解除，关闭报警输出
                    try:
                        self.plc_client.write_bool(2, 0, 0, False)
                    except Exception as e:
                        self.data_logger.log_message(f"写入PLC报警解除时发生错误: {e}")
                    info_msg = f"状态正常。温度: {temperature:.2f}, 压力: {pressure}, 电机运行: {motor_running}"
                    self.data_logger.log_message(info_msg)

                # 4. 等待下一次轮询
                time.sleep(self.poll_interval)

        except Exception as e:
            self.data_logger.log_message(f"监控循环发生未预期错误: {e}")
        finally:
            self.is_monitoring = False
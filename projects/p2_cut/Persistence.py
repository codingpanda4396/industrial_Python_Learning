from utils.s7util import Logger
class Persistence():
    def __init__(self):
        self.logger=Logger(__name__)
        self.logger.file_on()
        self.logger.screen_on()

    def save_flow_event(self,i, t0, t2, total_water, avg_params, avg_flow_rate):
        self.logger.info(f"""{i+1}流
                            进入时间:{t0}
                            出前12m时间:{t2}
                            总水量:{total_water}
                            各参数平均值：{avg_params}
                            平均流量：{avg_flow_rate}
                         """)
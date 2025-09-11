import socket
from utils.statepoint import *

class Tcp_server(socket.socket):
    """多线程处理、客户端管理、数据转换与回调、优雅停止"""
    def __init__(self, ip, port, backlog = 5, cli_max = 5, encoding = 'utf-8', point_t = Statepoint):
        super().__init__()#初始化父类

        self.backlog = backlog#最大挂起连接数
        self.cli_max = cli_max#允许的最大同时连接客户端数
        self.encoding = encoding#约定的字符编码
        self.point_t = point_t#状态点类型 

        self.run_flag = False   #服务器运行状态标志
        self.main_thread = None #主线程引用

        #StatePoint用到的函数
        self.convertor = lambda data: bool(data)    
        self.excite_action = lambda: None

        self.clients = {}   #客户端地址 : socket对象
        self.datas = {}     #客户端地址 : 最新接收数据
        self.points = {}    #客户端地址 : 状态点对象
        self.threads = {}   #客户端地址 : 处理线程对象

        self.bind((ip, port)) #将socket绑定到指定IP 和端口
        self.listen(backlog)  #开始监听，准备接受链接

    def accept_action(self):
        """持续接受新的客户端连接"""
        while self.run_flag:
            if len(self.clients) < self.cli_max:#不超过最大client数
                try:
                    cli, addr = self.accept()
                except OSError as e:
                    print('客户端等待连接服务被打断:', str(e))
                    self.run_flag = False
                    return None
                tmp_point = self.point_t()
                tmp_point.set_convertor(self.convertor)
                #tmp_point的激活动作：将状态点设为False 并执行服务器级别的激活动作
                tmp_point.set_excite_action(lambda t=tmp_point: (t.set_state(False), self.excite_action()))
                self.clients[addr] = cli
                self.datas[addr] = b''
                self.points[addr] = [tmp_point]
                #为该客户端创建专属数据处理线程
                self.threads[addr] = threading.Thread(target=self.update_action, args=(addr,))
                self.threads[addr].start()
                print(f'{addr}客户端已连接')
            else:
                time.sleep(1)

    def update_action(self, addr):
        """客户端专属线程，持续接收客户端发送的数据"""
        cli = self.clients[addr]#获取客户端
        noerror = True  #标记是否有error
        while self.run_flag:
            try:
                tmp = cli.recv(1024)#接收最多1024字节的数据
            except Exception as e:
                noerror = False
                tmp = b''   
                print(f'{addr}异常断连:{e}')
            if tmp:
                self.datas[addr] = tmp
                self.send(addr)
            else:
                break
        if noerror:
            print(f'{addr}正常断连')
        self.clients.pop(addr, None)
        self.datas.pop(addr, None)
        self.points.pop(addr, None)
        self.threads.pop(addr, None)

    def send(self, addr):
        if self.encoding:
            data = self.datas[addr].decode(encoding=self.encoding, errors='replace')
        else:
            data = self.datas[addr]

        for i in self.points[addr]:
            i.inject(data)

    def start(self):
        if self.main_thread and self.main_thread.is_alive():
            return None
        
        self.getsockname()
        self.main_thread = threading.Thread(target=self.accept_action)
        self.run_flag = True
        self.main_thread.start()

    def stop(self):
        if self.main_thread == None:
            return None
        
        self.run_flag = False #通知所有循环退出
        try:
            #创建一个临时客户端连接自己来打断主线程
            addr = self.getsockname()
            cli_tmp = socket.socket()
            cli_tmp.connect(addr)
            cli_tmp.close()
        finally:
            self.main_thread.join()#等待主线程安全结束
            self.main_thread = None

    def set_convertor(self, func):
        self.convertor = func

    def set_excite_action(self, func):
        self.excite_action = func

    def close(self):
        self.stop()
        return super().close()

    def send_to_all_clients(self, bytes_data: bytes):
        for i, j in self.clients.items():
            try:
                j.send(bytes_data)
            except Exception as e:
                print(f'{i}发送数据时产生异常:{e}')

import socket
from utils.statepoint import *

class Tcp_server(socket.socket):
    def __init__(self, ip, port, backlog = 5, cli_max = 5, encoding = 'utf-8', point_t = Statepoint):
        super().__init__()

        self.backlog = backlog
        self.cli_max = cli_max
        self.encoding = encoding
        self.point_t = point_t

        self.run_flag = False
        self.main_thread = None

        self.convertor = lambda data: bool(data)
        self.excite_action = lambda: None

        self.clients = {}
        self.datas = {}
        self.points = {}
        self.threads = {}

        self.bind((ip, port))
        self.listen(backlog)

    def accept_action(self):
        while self.run_flag:
            if len(self.clients) < self.cli_max:
                try:
                    cli, addr = self.accept()
                except OSError as e:
                    print('客户端等待连接服务被打断:', str(e))
                    self.run_flag = False
                    return None
                tmp_point = self.point_t()
                tmp_point.set_convertor(self.convertor)
                tmp_point.set_excite_action(lambda t=tmp_point: (t.set_state(False), self.excite_action()))
                self.clients[addr] = cli
                self.datas[addr] = b''
                self.points[addr] = [tmp_point]
                self.threads[addr] = threading.Thread(target=self.update_action, args=(addr,))
                self.threads[addr].start()
                print(f'{addr}客户端已连接')
            else:
                time.sleep(1)

    def update_action(self, addr):
        cli = self.clients[addr]
        noerror = True
        while self.run_flag:
            try:
                tmp = cli.recv(1024)
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
        
        self.run_flag = False
        try:
            addr = self.getsockname()
            cli_tmp = socket.socket()
            cli_tmp.connect(addr)
            cli_tmp.close()
        finally:
            self.main_thread.join()
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

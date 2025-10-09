from collections import deque
import datetime
import threading


class Statepoint:
    def __init__(self, initvalue = False, initstate = False):
        self.data = initvalue
        self.state = initstate
        self.hmd = set()
        self.lock = threading.Lock()
        self.permitted_update = True
        self.__private_permitted_update = True
        self.converter = lambda data: bool(data)
        self.do_excite = lambda: None
        self.do_reset = lambda: None
        self.keep_time = 1000
        self.pre_reset = False

    def hmd_add(self, data):
        self.hmd.add(data)

    def inject(self, data):
        if self.data == data or (self.hmd and data in self.hmd):
            return None
        #数据更新
        self.data = data
        #状态更新
        if self.permitted_update and self.__private_permitted_update:
            self.__async_update_state()
            #self.__update_state()

    def excite(self):
        #logger.info('excite to next')
        self.do_excite()

    def reset(self):
        self.do_reset()

    def __update_state(self):
        with self.lock:
            last_state = self.state
            self.state = self.converter(self.data)
            if last_state == False and self.state == True:
                self.pre_reset = False
                self.excite()
            elif last_state == True and self.state == False:
                if self.keep_time <= 0:
                    self.reset()
                elif self.pre_reset:
                    self.pre_reset = False
                    self.reset()
                else:
                    self.state = True
                    self.__private_allow_update(False)
                    self.pre_reset = True
                    timer = threading.Timer(self.keep_time/1000, lambda: self.__private_allow_update())
                    timer.start()
            elif last_state == True and self.state == True:
                self.pre_reset = False
            else:
                self.pre_reset = False

    def __async_update_state(self):
        threading.Thread(target=self.__update_state).start()

    def allow_update(self, enable: bool = True):
        self.permitted_update = enable
        if enable and self.__private_permitted_update:
            self.__async_update_state()
            #self.__update_state()

    def __private_allow_update(self, enable: bool = True):
        self.__private_permitted_update = enable
        if enable:
            self.__async_update_state()
            #self.__update_state()

    def set_convertor(self, func = lambda data: bool(data)):
        if callable(func):
            self.converter = func
        else:
            raise TypeError('The parameter func can only be a function')

    def set_excite_action(self, func = lambda: None):
        if callable(func):
            self.do_excite = func
        else:
            raise TypeError('The parameter func can only be a function')

    def set_reset_action(self, func = lambda: None):
        if callable(func):
            self.do_reset = func
        else:
            raise TypeError('The parameter func can only be a function')

    def set_keep_time(self, keeptime):
        self.keep_time = keeptime

    def set_state(self, state):
        self.state = state

class BufferPoint(Statepoint):
    def __init__(self, initvalue = None, initstate = False, maxlen: int | None = 3000):
        super().__init__(deque(maxlen = maxlen), initstate)

    def inject(self, data):
        self.data.append((data, datetime.datetime.now().timestamp()))

    def get_buffer(self):
        res = self.data.copy()
        last = res[-1][0]
        res.append((last, datetime.datetime.now().timestamp() + 0.001))#确保时间序列完整性
        return res
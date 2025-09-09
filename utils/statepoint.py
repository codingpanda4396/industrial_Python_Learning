import threading, time

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
            if self.permitted_update:
                self.allow_update(0)
                self.set_state(False)
                self.do_excite = func
                self.allow_update()
            else:
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

class Through_state_continues3(Statepoint):
    def __init__(self, p1, p2, p3):
        super().__init__()
        self.point1 = p1
        self.point2 = p2
        self.point3 = p3
        self.point1.allow_update(False)
        self.point2.allow_update(False)
        self.point3.allow_update(False)
        self.point1.set_excite_action(lambda: self.point2.allow_update())
        self.point2.set_excite_action(lambda: self.point3.allow_update())
        self.point3.set_excite_action(lambda: self.inject(True))
        
        self.point1.set_reset_action(lambda: (None if self.point2.state else self.point2.allow_update(False),
                                              None if self.point2.state or self.point3.state else self.inject(False)))
        self.point2.set_reset_action(lambda: (None if self.point3.state else self.point3.allow_update(False),
                                              None if self.point1.state else self.inject(False)))
        self.point3.set_reset_action(lambda: None if self.point2.state else self.inject(False))
        # self.set_excite_action(lambda: logger.info('经过点已触发'))
        # self.set_reset_action(lambda: logger.info('已前往推钢区域'))

    def reset(self):
        self.point2.allow_update(False)
        self.point3.allow_update(False)
        self.point3.state = False
        super().reset()
        if self.point1.state:
            self.point1.excite()

    def allow_update(self, enable: bool = True):
        if enable:
            self.point1.allow_update(enable)
        else:
            self.permitted_update = False
            self.point1.allow_update(False)
            self.point2.allow_update(False)
            self.point3.allow_update(False)
            self.point1.state = False
            self.point2.state = False
            self.point3.state = False
            self.permitted_update = True
            

class Through_state_separation2(Statepoint):
    def __init__(self, p1, p2):
        super().__init__()
        self.point1 = p1
        self.point2 = p2
        self.point1.allow_update(False)
        self.point2.allow_update(False)
        #self.point1.set_keep_time(3000)
        self.point1.set_excite_action(lambda: self.point2.allow_update())
        self.point2.set_excite_action(lambda: self.inject(True))
        
        self.point1.set_reset_action(lambda: None if self.point2.state else self.point2.allow_update(False))
        self.point2.set_reset_action(lambda: self.inject(False))
        # self.set_excite_action(lambda: logger.debug('推钢机已经推动钢坯'))

    def reset(self):
        self.point1.allow_update(False)
        self.point2.allow_update(False)
        self.point1.state = False
        self.point2.state = False
        #logger.debug('推钢机刚刚经过')
        super().reset()
        self.point1.allow_update()

    def allow_update(self, enable: bool = True):
        if enable:
            # logger.debug('open')
            self.point1.allow_update()
        else:
            # logger.debug('close')
            self.permitted_update = False
            self.point1.allow_update(False)
            self.point2.allow_update(False)
            self.point1.state = False
            self.point2.state = False
            self.permitted_update = True

class Integration_speed_mpmin(Statepoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.last_inject_time = time.time()
        self.last_data = 0
        self.last_data_time = self.last_inject_time

    def inject(self, data):
        current_inject_time = time.time()
        current_data = data
        current_data_time = self.last_inject_time + (current_inject_time - self.last_inject_time) / 2

        data = self.data + (current_data_time - self.last_data_time) * (self.last_data + current_data) / 120

        self.last_inject_time = current_inject_time
        self.last_data = current_data
        self.last_data_time = current_data_time

        return super().inject(data)
    
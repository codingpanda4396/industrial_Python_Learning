import threading, time

# 基于状态转换的异步处理框架
class Statepoint:
    def __init__(self, initvalue = False, initstate = False):
        self.data = initvalue  #当前数据值
        self.state = initstate #当前状态
        self.hmd = set()       #黑名单集合
        self.lock = threading.Lock() #确保状态更新原子性
        self.permitted_update = True #公有更新许可
        self.__private_permitted_update = True #私有更新许可
        self.converter = lambda data: bool(data)
        self.do_excite = lambda: None
        self.do_reset = lambda: None
        self.keep_time = 1000 #状态保持时间
        self.pre_reset = False #是否处于保持期

    def hmd_add(self, data):
        self.hmd.add(data)

    def inject(self, data):
        if self.data == data or (self.hmd and data in self.hmd):
            return None #数据无变化或在黑名单中则忽略
        #数据更新
        self.data = data
        #状态更新
        if self.permitted_update and self.__private_permitted_update:#允许更新
            self.__async_update_state()#异步更新状态
            #self.__update_state()

    def excite(self):
        #logger.info('excite to next')
        self.do_excite()

    def reset(self):
        self.do_reset()

    def __update_state(self):
        with self.lock: #加锁
            last_state = self.state #获取当前状态
            self.state = self.converter(self.data) #将data转换为state

            #False->True  触发excite
            if last_state == False and self.state == True:
                self.pre_reset = False
                self.excite()
                #True->False 启动保持定时器或重置
            elif last_state == True and self.state == False:
                if self.keep_time <= 0:#无状态保持时间 则重置
                    self.reset()
                elif self.pre_reset:#保持期内再次收到false，立即重置
                    self.pre_reset = False
                    self.reset()
                else:#保持期内，发生True->False
                    self.state = True #保持当前状态
                    self.__private_allow_update(False) #暂停私有更新
                    self.pre_reset = True #进入预重置状态
                    #设置保持定时器（延迟keep_time/1000秒 执行“允许私有更新”操作）
                    timer = threading.Timer(self.keep_time/1000, lambda: self.__private_allow_update())
                    timer.start()
            #True—>True和其他情况--清除预重置，维持原状态
            elif last_state == True and self.state == True:
                self.pre_reset = False
            else:
                self.pre_reset = False

    def __async_update_state(self):#异步状态更新
        threading.Thread(target=self.__update_state).start()

    def allow_update(self, enable: bool = True):
        self.permitted_update = enable #更新公有更新许可
        if enable and self.__private_permitted_update:
            self.__async_update_state()#允许更新&&私有许可True 时立即触发一次异步状态更新
            #self.__update_state()

    def __private_allow_update(self, enable: bool = True):#控制私有状态更新许可
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
            if self.permitted_update:#允许更新则临时禁用更新
                self.allow_update(0)
                self.set_state(False)# 当前状态强制设为false
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
        self.keep_time = keeptime#防抖动机制

    def set_state(self, state):
        self.state = state

class Integration_speed_mpmin(Statepoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.last_inject_time = time.time() #上次注入数据的时间戳
        self.last_data = 0  #上次注入的数据值
        self.last_data_time = self.last_inject_time #上次数据有效的时间点

    def inject(self, data):
        current_inject_time = time.time()
        current_data = data
        #估算当前数据有效时间点
        current_data_time = self.last_inject_time + (current_inject_time - self.last_inject_time) / 2

        #梯形积分更新长度值
        data = self.data + (current_data_time - self.last_data_time) * (self.last_data + current_data) / 120


        #为下一次做准备
        self.last_inject_time = current_inject_time
        self.last_data = current_data
        self.last_data_time = current_data_time

        return super().inject(data)
    

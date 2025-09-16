import threading, time

class Statepoint:
    """数据驱动状态转换，并在转换时做相应的操作
    （False->True excite）
     (True->False reset)
     （converter是数据转换成状态的逻辑）
     提供了防抖机制，True->False时启动定时器，在定时器时间到后若确实是False，状态才会变为false
    """
    def __init__(self, initvalue = False, initstate = False):
        self.data = initvalue #数据
        self.state = initstate#状态
        self.hmd = set()#黑名单 用于过滤不希望触发更新的特定数据值
        self.lock = threading.Lock()# 确保状态更新操作的线程安全。
        self.permitted_update = True #公有允许更新标记 为 False时阻塞由 inject方法触发的状态更新。
        self.__private_permitted_update = True #私有允许更新标记 用于实现内部延迟重置逻辑
        self.converter = lambda data: bool(data) #数据->状态转换器 将 data转换为布尔类型的 state。
        self.do_excite = lambda: None #激活 在状态从 False变为 True时被调用。
        self.do_reset = lambda: None  #重置 在特定条件下状态从 True变为 False时被调用。
        self.keep_time = 1000         #设置在状态即将变为 False时，延迟重置的等待时间。
        self.pre_reset = False #标记是否进入延迟重置状态 
        #True -> 标识系统已经进入了延迟重置状态
        #False->系统没有延迟重置请求 | 延迟重置已经完成

    def hmd_add(self, data):
        self.hmd.add(data)

    def inject(self, data):
        """向状态点注入新数据"""
        if self.data == data or (self.hmd and data in self.hmd):
            return None
        #数据有效->数据更新
        self.data = data
        #公有、私有更新标记均为True->异步触发状态更新
        if self.permitted_update and self.__private_permitted_update:
            self.__async_update_state()
            #self.__update_state()

    def excite(self):
        #logger.info('excite to next')
        self.do_excite()

    def reset(self):
        self.do_reset()

    def __update_state(self):
        with self.lock:#保证线程安全
            last_state = self.state#记录当前状态
            self.state = self.converter(self.data)#计算新状态
            #False->True 
            if last_state == False and self.state == True:
                self.pre_reset = False#清除标记，激活
                self.excite()
            #True->False
            elif last_state == True and self.state == False:
                if self.keep_time <= 0:#没有设置延迟重置
                    self.reset()
                elif self.pre_reset:#延迟时间已到
                    self.pre_reset = False
                    self.reset()
                else:   #pre_reset==False且有延迟重置->系统尚未进入延迟重置状态 
                    self.state = True #当前状态保持为True->有一个重置请求待处理 
                    self.__private_allow_update(False)#不允许私有更新
                    self.pre_reset = True
                    #定时器到期后允许私有更新并再次调用本函数   
                    timer = threading.Timer(self.keep_time/1000, lambda: self.__private_allow_update())
                    timer.start()
            elif last_state == True and self.state == True:
                self.pre_reset = False
            else:
                self.pre_reset = False

    def __async_update_state(self):
        threading.Thread(target=self.__update_state).start()

    def allow_update(self, enable: bool = True):
        """允许公有状态更新(如果内部也允许状态更新，则启动一个异步更新线程)"""
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
    """管理三个连续状态点的激活与重置逻辑，实现一个三步的顺序流程控制"""
    def __init__(self, p1:Statepoint, p2:Statepoint, p3:Statepoint):
        super().__init__()
        self.point1 = p1
        self.point2 = p2
        self.point3 = p3
        self.point1.allow_update(False)
        self.point2.allow_update(False)
        self.point3.allow_update(False)
        self.point1.set_excite_action(lambda: self.point2.allow_update())#p1激活->允许p2更新
        self.point2.set_excite_action(lambda: self.point3.allow_update())#p2激活->允许p3更新
        self.point3.set_excite_action(lambda: self.inject(True))#给类本身注入True
        
        #p2未激活->禁用p2自动更新  p2、p3均未激活->重置自身
        self.point1.set_reset_action(lambda: (None if self.point2.state else self.point2.allow_update(False),
                                              None if self.point2.state or self.point3.state else self.inject(False)))
        #p3未激活->禁用p3自动更新 p1未激活->重置自身
        self.point2.set_reset_action(lambda: (None if self.point3.state else self.point3.allow_update(False),
                                              None if self.point1.state else self.inject(False)))
        #p2未激活则重置自身
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
    """管理两个分离状态点的激活与重置逻辑，通常用于二元操作流程。"""
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
    """对输入数据（如速度信号）进行积分计算，得到累计量（如位移、产量累计）。"""
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
    
import threading
import time
from enum import Enum

class CollectorState(Enum):
    MOVING = 1
    COLLECTING = 2
    LEAVING = 3

class Statepoint:
    def __init__(self, initvalue=False, initstate=False):
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

    def inject(self, data):
        if self.data == data or (self.hmd and data in self.hmd):
            return None
        self.data = data
        if self.permitted_update and self.__private_permitted_update:
            self.__async_update_state()

    def excite(self):
        self.do_excite()

    def reset(self):
        self.do_reset()

    def __update_state(self):
        try:
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
        except Exception as e:
            print(f"Error in __update_state: {e}")

    def __async_update_state(self):
        threading.Thread(target=self.__update_state).start()

    def allow_update(self, enable: bool = True):
        self.permitted_update = enable
        if enable and self.__private_permitted_update:
            self.__async_update_state()

    def __private_allow_update(self, enable: bool = True):
        self.__private_permitted_update = enable
        if enable:
            self.__async_update_state()

    def set_convertor(self, func=lambda data: bool(data)):
        if callable(func):
            self.converter = func
        else:
            raise TypeError('The parameter func can only be a function')

    def set_excite_action(self, func=lambda: None):
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

    def set_reset_action(self, func=lambda: None):
        if callable(func):
            self.do_reset = func
        else:
            raise TypeError('The parameter func can only be a function')

    def set_keep_time(self, keeptime):
        self.keep_time = keeptime

    def set_state(self, state):
        self.state = state

class CollectionSystem:
    def __init__(self):
        self.production_lines = [1000 + i * 1000 for i in range(8)]
        self.current_line_index = 0
        self.collector_position = 0.0
        self.collection_speed = 500.0
        self.collection_tolerance = 50.0
        self.target_position = self.production_lines[self.current_line_index]
        self.state = CollectorState.MOVING
        self.lock = threading.Lock()

        self.position_state = Statepoint(initvalue=0.0, initstate=False)
        self._update_converter()#更新转换器，用来判断收集器到达与否的状态
        self.position_state.set_excite_action(self.on_arrive_at_collection_point)#收集钢坯动作
        self.position_state.set_reset_action(self.on_leave_collection_point)#安排下一个任务、更新convertor
        self.position_state.set_keep_time(2000)#True变为False时的防抖时间
        
        self.running = True

    def _update_converter(self):
        """更新状态转换器，使用默认参数绑定当前目标值"""
        with self.lock:
            current_target = self.target_position
        self.position_state.set_convertor(lambda pos, target_val=current_target: abs(pos - target_val) <= self.collection_tolerance)

    def on_arrive_at_collection_point(self):
        print(f"\033[92m[动作] 收集设备已到达生产线{self.current_line_index+1} (位置: {self.target_position})，开始收集钢坯...\033[0m")
        with self.lock:
            self.state = CollectorState.COLLECTING
        leave_timer = threading.Timer(self.position_state.keep_time / 1000, self._leave_collection_point)
        leave_timer.start()

    def _leave_collection_point(self):
        """由定时器调用，主动让设备离开容差范围以触发状态转换"""
        with self.lock:
            if self.state != CollectorState.COLLECTING:
                return
            self.state = CollectorState.LEAVING
            leave_position = self.target_position + self.collection_tolerance + 10
            print(f"[调试] 收集完成，主动移动到位置 {leave_position} 以触发状态重置...")
            self.collector_position = leave_position
        self.position_state.inject(leave_position)

    def on_leave_collection_point(self):
        print(f"\033[93m[动作] 离开生产线{self.current_line_index+1}，准备移向下一生产线...\033[0m")
        with self.lock:
            self.state = CollectorState.MOVING
            self.current_line_index = (self.current_line_index + 1) % len(self.production_lines)
            self.target_position = self.production_lines[self.current_line_index]
        print(f"[状态] 新目标: 生产线{self.current_line_index+1} (位置: {self.target_position})")
        self._update_converter()

    def update_collector_position(self, new_position):
        with self.lock:
            self.collector_position = new_position
        self.position_state.inject(new_position)

    def simulate_collector_movement(self):
        while self.running:
            with self.lock:
                if self.state == CollectorState.COLLECTING or self.state == CollectorState.LEAVING:
                    time.sleep(0.1)
                    continue

                current_target = self.target_position
                current_pos = self.collector_position
                direction = 1.0 if current_target > current_pos else -1.0
                distance_to_target = abs(current_target - current_pos)
                move_increment = min(self.collection_speed * 0.1, distance_to_target) * direction
                new_pos = current_pos + move_increment
            
            self.update_collector_position(new_pos)
            
            with self.lock:
                current_pos_display = self.collector_position
                current_target_display = self.target_position
                current_state_display = self.state
            status = "已到达" if self.position_state.state else "移动中"
            print(f"[移动] 设备位置: {current_pos_display:.2f}, 目标位置: {current_target_display}, 状态: {status}, 系统状态: {current_state_display.name}")
            
            time.sleep(0.1)

    def start_simulation(self, simulation_duration=30):
        print(f"[系统] 启动模拟，共有{len(self.production_lines)}条生产线，位置: {self.production_lines}")
        print(f"[系统] 初始目标: 生产线{self.current_line_index+1} (位置: {self.target_position})")
        
        movement_thread = threading.Thread(target=self.simulate_collector_movement, daemon=True)
        movement_thread.start()
        
        try:
            time.sleep(simulation_duration)
        except KeyboardInterrupt:
            print("\n[系统] 用户中断模拟。")
        finally:
            self.running = False
            print("[系统] 模拟结束。")

if __name__ == "__main__":
    system = CollectionSystem()
    system.start_simulation(simulation_duration=30)
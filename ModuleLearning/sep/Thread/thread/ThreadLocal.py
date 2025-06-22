import threading

local_school=threading.local()

def process_student():
    # 获取当前线程关联的student:
    std = local_school.student
    print('Hello, %s (in %s)' % (std, threading.current_thread().name))

def process_thread(name):
    # 绑定ThreadLocal的student:
    local_school.student = name
    process_student()


t1=threading.Thread(target=process_thread,args=('Panda',),name='Thread-A')
t2=threading.Thread(target=process_thread,args=('Bob',),name='Thread-B')
t1.start()
t2.start()
print('主线程等待...')
t1.join() #阻塞主线程、waiting t1 t2执行结束
t2.join()

print('主线程结束')
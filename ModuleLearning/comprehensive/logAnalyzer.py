import threading 
import json
import os
def analyze_log(filepath):
    errors=[]
    with open(filepath) as f:
        for line in f:#遍历文件找出ERROR
            if "ERROR" in line: 
                errors.append(line.strip())
    return {filepath:errors}#字典中嵌套list

threads=[]
results={}
logfiles=os.listdir("")
for logfile in logfiles:
    t=threading.Thread(target=analyze_log,args=(logfile,))
    t.start()
    threads.append(t)

import queue
import random
import time
import mutl_climb
import threading

def do_craw(url_queue:queue.Queue,html_queue:queue.Queue):#生产者线程
    while True:
        url=url_queue.get()#url队列中拿出url
        html = mutl_climb.craw(url)#发送请求爬取数据
        html_queue.put(html)#放入html队列中
        print(threading.current_thread().name,f"craw {url}",
              "url_queue.size=",url_queue.qsize())#log
        time.sleep(random.randint(1,2))#每次爬取后休息

def do_parse(html_queue:queue,fout):#消费者线程  
    while True:
        html=html_queue.get()#html
        results=mutl_climb.parse(html)#接续爬取到的html
        for result in results:
            fout.write(str(result)+'\n')#写入文件
        print(threading.current_thread().name,f"results size", len(results),
              "html_queue.size=",html_que.qsize())
        time.sleep(random.randint(1,2))

if __name__ == "__main__":
    url_que=queue.Queue()
    html_que=queue.Queue()

    for url in mutl_climb.urls:
        url_que.put(url)
    for idx in range(3):# 三个producer线程
        t=threading.Thread(target=do_craw,args=(url_que,html_que),
                           name=f"craw{idx}")
        t.start()
        
    fout=open("craw02.txt","w")
    for idx in range(2):#两个consumer线程
        t=threading.Thread(target=do_parse,args=(html_que,fout),name=f"produce{idx}")
        t.start()
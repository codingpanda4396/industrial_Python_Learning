import mutl_climb
import threading
import time
def single():
    print("single start")
    for url in mutl_climb.urls:
        mutl_climb.craw(url)
    print("single finish")

def multi_thread():
    print("mutl start")
    threads=[]#创建一个list
    for url in mutl_climb.urls:
        threads.append(
            threading.Thread(target=mutl_climb.craw,args=(url,))
        )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()       
    print("mutl finish")

    if __name__ == "__main__":
        start=time.time()
        multi_thread()
        end=time.time()
        print(end-start)
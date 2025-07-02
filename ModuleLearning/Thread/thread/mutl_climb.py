import requests

urls=[
     f"https://www.cnblogs.com/#p{page}"
        for page in range(1,51)
     ]

def craw(url):
    r=requests.get(url)
    print(url,len(url))

craw(urls[0])
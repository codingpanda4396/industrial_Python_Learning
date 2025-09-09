import concurrent.futures
import mutl_climb

with concurrent.futures.ThreadPoolExecutor() as pool:
    htmls = pool.map(mutl_climb.craw,mutl_climb.urls) 
    htmls = list(zip(mutl_climb.urls,htmls))
    for url,html in htmls:
        print(url,len(html))



with concurrent.futures.ThreadPoolExecutor() as pool:
    futures = {}
    for url,html in htmls:
        future = pool.submit(mutl_climb.parse,html)
        futures[future]=url

    for future,url in futures.items():
        print(url,future.result())
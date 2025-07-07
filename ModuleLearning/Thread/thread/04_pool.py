import concurrent.futures
import mutl_climb

with concurrent.futures.ThreadPoolExecutor() as pool:
    htmls = pool.map(mutl_climb.craw,mutl_climb.urls)
    htmls = list(zip(mutl_climb.urls,htmls))
import logging

#1 创建基础组件--logger(记录器)
logger=logging.getLogger("my logger")
logger.setLevel(logging.DEBUG)#设置级别为DEBUG

#2 创建控制台处理器（handler）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # 控制台只输出WARNING及以上

# 3. 创建文件处理器（记录所有级别）
file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.DEBUG)

#4.设置日志格式
formatter=logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# 5. 添加处理器到记录器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 6. 记录日志
logger.debug("Debug details")      # 仅写入文件
logger.warning("Potential issue")  # 输出到控制台和文件

"""
配置handler之后，将handler加入logger就可以记录日志了
"""
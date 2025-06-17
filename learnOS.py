import os
# get current work dirctory
print(os.getcwd())



# 显示路径下所有文件和目录组成的列表
path=r'D:\CodingPanda'
print(os.listdir(path))


for paths,dirs,files in os.walk(path):
    print(path)
    print(dirs)
    print(files)
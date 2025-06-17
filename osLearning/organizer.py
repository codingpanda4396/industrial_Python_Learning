import os
# “文件整理器”
'''
扫描指定目录及其子目录，根据文件扩展名将它们分类移动到对应的目标文件夹中
'''
print("输入需要整理的源路径")
src=input()
print("输入整理后的目标路径")
dst=input()
print("正在整理...")

count=0

for dirpath,dirnames,filenames in os.walk(src):#层次遍历源路径中的信息（当前路径、子目录列表、文件名列表）
    print('开始遍历{}',dirpath)
    for filename in filenames:#遍历文件名列表
        if os.path.isfile(os.path.join(dirpath,filename)):#检查是否为文件
            count+=1
            root,ext= os.path.splitext(filename)#提取出文件扩展名
            realDst = os.path.join(dst,ext[1:])#扩展名链接目标路径，生成文件存放路径(去掉开头的.)
            if not os.path.exists(realDst): #如果还没有创建相应“扩展名文件夹”
                os.makedirs(realDst)#创建“扩展名文件夹”
                print("创建目录:{}",realDst)
            
            srcDir=os.path.join(dirpath,filename)#获取文件源路径
            dstDir=os.path.join(dst,ext[1:],filename)#获取将要移动到的路径
            if os.path.exists(dstDir):#如果目标处已经存在文件
                dstDir=os.path.join(dst,ext[1:],filename+str(count))#获取将要移动到的路径
            os.rename(srcDir,dstDir)#移动文件
            print('移动文件{}->{}',srcDir,dstDir)
print("找到了{}个文件",count)

      



        
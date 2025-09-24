import socket
import os

def client(file_path):
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return
    
    # 获取文件名和文件大小
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # 创建一个socket对象
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 获取本地主机名
    host = input("host:")
    port = 12345
    
    # 连接服务，指定主机和端口
    s.connect((host, port))
    
    # 发送文件名和文件大小
    s.send(f"{file_name}|{file_size}".encode())
    
    # 接收确认信息
    response = s.recv(1024).decode()
    if response != "READY":
        print("服务器未准备好接收文件")
        s.close()
        return
    
    # 发送文件内容并显示进度条
    sent_size = 0
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            s.send(data)
            sent_size += len(data)
            # 计算进度百分比
            progress = sent_size / file_size * 100
            # 生成进度条
            bar_length = 50
            filled_length = int(bar_length * sent_size // file_size)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            # 打印进度条 (覆盖当前行)
            print(f'\r发送进度: [{bar}] {progress:.1f}%', end='')
    
    print('\n文件发送完成')
    s.close()

if __name__ == '__main__':
    # 使用示例：修改为你要传输的文件路径
    file_to_send = input("file:")
    client(file_to_send)    

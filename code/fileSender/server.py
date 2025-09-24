import socket
import os

def server():
    # 创建一个socket对象
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 获取本地主机名
    host = "0.0.0.0"
    port = 12345
    
    # 绑定端口
    s.bind((host, port))
    
    # 设置最大连接数，超过后排队
    s.listen(5)
    
    print("服务器已启动，等待连接...")
    
    while True:
        # 建立客户端连接
        clientsocket, addr = s.accept()
        print(f"连接地址: {str(addr)}")
        
        # 接收文件名和文件大小
        file_info = clientsocket.recv(1024).decode()
        file_name, file_size = file_info.split('|')
        file_size = int(file_size)
        
        # 检查文件是否已存在，避免覆盖
        base_name, ext = os.path.splitext(file_name)
        counter = 1
        new_file_name = file_name
        while os.path.exists(new_file_name):
            new_file_name = f"{base_name}_{counter}{ext}"
            counter += 1
        
        # 发送准备好接收的确认信息
        clientsocket.send("READY".encode())
        
        # 接收文件内容并显示进度条
        received_size = 0
        with open(new_file_name, 'wb') as f:
            while received_size < file_size:
                data = clientsocket.recv(1024)
                if not data:
                    break
                f.write(data)
                received_size += len(data)
                # 计算进度百分比
                progress = received_size / file_size * 100
                # 生成进度条
                bar_length = 50
                filled_length = int(bar_length * received_size // file_size)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                # 打印进度条 (覆盖当前行)
                print(f'\r接收进度: [{bar}] {progress:.1f}%', end='')
        
        print(f'\n文件 {new_file_name} 接收完成')
        clientsocket.close()

if __name__ == '__main__':
    server()    
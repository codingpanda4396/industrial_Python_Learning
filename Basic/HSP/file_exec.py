from datetime import datetime
nameList=["smith",'tom','hsp']
password='888'

def login_to_file(name:str,status:int):
    with open("login_log.txt",'a',encoding="utf-8") as f:
        f.write(f"登录用户{name} 登录{"成功"if status==1 else "失败"} 登陆时间{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}\n")

def file_print():
    with open("login_log.txt","r",encoding="utf-8") as f:
        text= f.read()
        print(text)

if __name__ == "__main__":  
    username= input("请输入用户名")
    pwd= input("请输入密码")

    singnal=0#判断是否通过验证
    for name in nameList:
        if username==name:
            if pwd==password:
                singnal=1
                print("登陆成功")
                print("1 查看当前登录用户")
                print("2 查看登录日志")
                print("3 exit")
    login_to_file(username,singnal)
    
    while(True):
        choice=input("请输入你的选择：")
        match choice:
            case '1':
                print(f"当前登录用户{username}")
                continue
            case '2':
                file_print()
                continue
            case '3':  
                break
    
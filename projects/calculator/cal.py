def basic_calculator():
    print("🧮 Python基础计算器")
    print("支持运算：+（加） -（减） *（乘） /（除） %（取模）")
    try:
        num1=float(input("输入第一个数字："))
        operator = input("输入运算符 (+, -, *, /, %): ")
        num2 = float(input("输入第二个数字: "))
        # 执行计算
        if operator == '+':
            result = num1 + num2
        elif operator == '-':
            result = num1 - num2
        elif operator == '*':
            result = num1 * num2
        elif operator == '/':
            if num2==0:
                raise ZeroDivisionError
            result=num1/num2
        elif operator == '%':
            result=num1 %num2
        else:
            raise ValueError("无效运算符")

        print(f"结果: {num1} {operator} {num2} = {result:.2f}")
    
    except ZeroDivisionError:
        print("错误：除数不能为0！")
    except ValueError as e:
        print(f"输入错误: {e}")
    except Exception:
        print("未知错误，请检查输入")
def advanced_calculator():
    print("🚀 增强版计算器 - 支持连续运算（输入'='结束）")
    expression = []  # 存储表达式
    
    # 首次输入
    expression.append(float(input("输入第一个数字: ")))
    
    while True:
        operator = input("输入运算符 (+, -, *, /, %) 或输入 = 结束: ")
        if operator == '=':
            break
            
        if operator not in ['+', '-', '*', '/', '%']:
            print("无效运算符，请重新输入")
            continue
        
        num = float(input("输入下一个数字: "))
        
        expression.append(operator)
        expression.append(num)
    
    result = expression[0]
    for i in range(1, len(expression), 2):
        op = expression[i]
        next_num = expression[i+1]
        
        if op == '+': result += next_num
        elif op == '-': result -= next_num
        elif op == '*': result *= next_num
        elif op == '/':
            if next_num == 0:
                print("错误：除数不能为0！")
                return
            result /= next_num
        elif op == '%': result %= next_num
    
    # 显示完整表达式和结果
    expr_str = " ".join(str(x) for x in expression)
    print(f"{expr_str} = {result:.2f}")



if __name__=="__main__":
    advanced_calculator()9
import sqlite3
import numpy as np

temp_limit = (760, 870)

conn = sqlite3.connect("steel_production_data1.db")
cursor = conn.cursor()

cursor.execute("select tail_steel_length_laser, tail_steel_length_thermal, fixed_length from production_data")
length_list = cursor.fetchall()

conn.close()

standard = 832

solved_list = []
last_length = length_list[0][0]
for i, j, k in length_list:
    if i == last_length:
        continue
    last_length = i
    if k < 10000:
        continue
    i *= 10
    if (j == temp_limit[0] and i < j) or (j == temp_limit[1] and i > j):
        solved_list.append(i)
    elif abs(i-j) < 10:
        solved_list.append(i)
    else:
        solved_list.append(j)

diff = [i-standard for i in solved_list]
variance = np.mean([i**2 for i in diff])
sd = np.sqrt(variance)
print('统计结果：')
print('差值平均：', np.mean(diff))
print('最大差值：', max([abs(i) for i in diff]))
print('最小差值：', min([abs(i) for i in diff]))
print('\n标 准 差：', np.std(solved_list))
print('方    差：', np.var(solved_list))
print('标准差(基于设定尾钢长度)：', sd)
print('方  差(基于设定尾钢长度)：', variance)

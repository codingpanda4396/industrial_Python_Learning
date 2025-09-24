import sqlite3, datetime, csv

temp_limit = (760, 870)

conn = sqlite3.connect("steel_production_data3.db")
cursor = conn.cursor()

cursor.execute("select * from production_data")
data_list = cursor.fetchall()

conn.close()

solved_list = []
has_steel_sig = 1
counter = 1
last_length = data_list[0][9]

input_buffer = []
for data in data_list:
    if data[3] == 0 and has_steel_sig != 0:
        last_length = 0

        strand_no = int(data[6])
        if strand_no > 8 or strand_no != 2:
            continue

        timestamp = datetime.datetime.strptime(data[1], "%Y-%m-%d %H:%M:%S.%f").timestamp()
        tmp = [counter, timestamp, data[5], data[19+strand_no-1], data[28], data[27], data[8], data[10]]
        counter += 1
        tmp_2 = [data[29+i] for i in range(36)]

        input_buffer = tmp + tmp_2
    
    if data[9]*10 != last_length:
        last_length = data[9]*10
        if input_buffer:
            if (data[7] == temp_limit[0] and data[9]*10 < data[7]) or (data[7] == temp_limit[1] and data[9]*10 > data[7]):
                solved_list.append((input_buffer, data[9]*10))
            elif abs(data[9]*10-data[7]) < 10:
                solved_list.append((input_buffer, data[9]*10))
            else:
                solved_list.append((input_buffer, data[7]))
            input_buffer = []
    
    has_steel_sig = data[3]

output_list = []
for i in range(len(solved_list)-1):
    tmp = solved_list[i][0][:]
    next = solved_list[i+1]
    tmp.append((next[0][4]-next[1])*next[0][5]/10 + next[0][3])
    output_list.append(tmp)

# 写入 CSV 文件
with open("output.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(output_list)

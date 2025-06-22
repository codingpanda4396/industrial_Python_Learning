import pickle
d=dict(name='Bob',age=20,score=88)
p=pickle.dumps(d)
print(p)

with open("C:\\Users\\14690\\Desktop\\hello.txt",'rb') as f:
    dic=pickle.load(f)


print(dic)
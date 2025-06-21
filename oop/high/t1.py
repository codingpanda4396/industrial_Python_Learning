class Student(object):
    __slots__=('name','age')

s=Student()
s.name="panda"
print(s.name)# 动态语言的灵活性
#s.sex='male'
#AttributeError: 'Student' object has no attribute 'sex' and no __dict__ for setting new attribute 
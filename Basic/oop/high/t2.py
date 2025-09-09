# class Student(object):
#     @property
#     def score(self):
#         return self._score
#     @score.setter
#     def score(self,value):
#         if not isinstance(value, int):
#             raise ValueError('score must be an integer!')
#         if value < 0 or value > 100:
#             raise ValueError('score must between 0 ~ 100!')
#         self._score = value

class Screen(object):
    @property
    def getWidth(self):
        return self.width
    @getWidth.setter
    def setWidth(self,wid):
        self.width=wid
    @property
    def getHeight(self):
        return self.height
    @getHeight.setter
    def setHeight(self,height):
        self.height=height
    @property
    def resolution(self):
        self._resolution=self.width*self.height
        return self._resolution


# 测试:
s = Screen()
s.width = 1024
s.height = 768
print('resolution =', s.resolution)
if s.resolution == 786432:
    print('测试通过!')
else:
    print('测试失败!')

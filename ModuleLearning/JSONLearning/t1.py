import json

data = {
    "name": "John",
    "age": 30,
    "city": "New York",
    "married": False,
    "children": None,
    "pets": ["dog", "cat"]
}

json_str=json.dumps(data)#这个方法用来将python对象序列化为字符串
print(json_str)

dict=json.loads(json_str)
print(dict['name'])



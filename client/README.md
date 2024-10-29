# k-v store client
k-v store的客户端程序使用说明

## 支持的功能
1. 根据key查询它的value
2. 增加一个key-value
3. 删除一个key相关的信息
4. 支持批量接口
5. 支持三种输出模式：标准的格式，输出json, 输出table.

## 使用说明
1. 根据key查询它的value
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first
first: alice

```

2. 增加一个key-value
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py put first=alice
success
ubuntu@mpi-node1:~/k-v/client$ python3 client.py put second=alice
success
ubuntu@mpi-node1:~/k-v/client$ python3 client.py put third=jack
success

```
3. 删除一个key相关的信息
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py delete third
deleted
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first,second,third --table
+--------+-------+---------+
| Key    | Value | Status  |
+--------+-------+---------+
| first  | alice | success |
| second | alice | success |
| third  |       | error   |
+--------+-------+---------+

```
4. 支持批量接口
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first,second --table
+--------+-------+---------+
| Key    | Value | Status  |
+--------+-------+---------+
| first  | alice | success |
| second | alice | success |
+--------+-------+---------+

```

5. 支持三种输出模式：标准的格式，输出json, 输出table.
标准输出:

```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first
first: alice
```

json格式输出:
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first --json
{
    "first": {
        "key": "first",
        "status": "success",
        "value": "alice"
    }
}
```

table格式输出:
```
ubuntu@mpi-node1:~/k-v/client$ python3 client.py get first,second,third --table
+--------+-------+---------+
| Key    | Value | Status  |
+--------+-------+---------+
| first  | alice | success |
| second | alice | success |
| third  | jack  | success |
+--------+-------+---------+

```



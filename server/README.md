# k-v store server
k-v store用于存储key-value数据

## 架构说明
存储服务端，分成三层:    
最上层为web层，使用flask提供http服务，支持k-v的get/put/delete操作。   
中间一层为Chord DHT层，使用BSD Socket进行通信, 用于控制Chord DHT相关的操作。    
最底层为DB层，用于存储K-V， 目前使用leveldb来存储k-v相关的数据。


## 使用说明
### 依赖
k-v store server程序依赖包:
```
pip3 install flask plyvel
```
### 命令说明
1. server.py 不带参数为启动seed结点      
2. 带上参数表示启动普通节点          
参数说明：        
第一个参数为Seed node的地址，默认seed node为6000端口，如果是本机则写: 0.0.0.0:6000        
第二个参数为Chord Server的本地端口，可以任意指定，比如：8000      
第三个参数为HTTP Server 的本地端口，要指定一个与Chord Server不冲突的端口，如：7000    

### 使用样例:

k-v store seed node的启动命令:
```
python3 server.py
```
k-v store 普通节点的启动命令:
```
python3 server.py 0.0.0.0:6000 8000 7000
```

将会得到以下输出，说明程序运行正常:   

```
ubuntu@mpi-node1:~/k-v/server$ python3 server.py 
INFO:ChordNode 8226:Listening on 0.0.0.0:6000
 * Serving Flask app 'server'
 * Debug mode: off
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.12.11:5000
INFO:werkzeug:Press CTRL+C to quit

```

当程序有以上输出的时候，可以等待客户端的连接。



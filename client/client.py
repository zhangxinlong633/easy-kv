import requests
import json
import argparse
from prettytable import PrettyTable
from colorama import Fore, Style

# 定义基本的 URL，用于请求 K-V 存储服务
BASE_URL = 'http://localhost:5000'

def put(keys_values):
    """ 批量添加键值对到 K-V 存储 """
    results = {}
    for key, value in keys_values.items():
        url = f'{BASE_URL}/put'  # 拼接 PUT 请求的 URL
        data = {'key': key, 'value': value}  # 构造请求数据
        response = requests.post(url, json=data)  # 发送 POST 请求
        if response.status_code == 200:
            results[key] = response.json()  # 将响应结果存储到字典中
        else:
            results[key] = {'status': 'error', 'message': response.text}  # 处理错误响应
    return results  # 返回所有结果

def get(keys):
    """ 批量获取 K-V 存储中的值 """
    results = {}
    for key in keys:
        url = f'{BASE_URL}/get/{key}'  # 拼接 GET 请求的 URL
        response = requests.get(url)  # 发送 GET 请求
        if response.status_code == 404:
            results[key] = {'status': 'error', 'message': 'Key not found'}  # 处理未找到的键
        else:
            results[key] = response.json()  # 将响应结果存储到字典中
    return results  # 返回所有结果

def delete(keys):
    """ 批量删除 K-V 存储中的键 """
    results = {}
    for key in keys:
        url = f'{BASE_URL}/delete/{key}'  # 拼接 DELETE 请求的 URL
        response = requests.delete(url)  # 发送 DELETE 请求
        if response.status_code == 404:
            results[key] = {'status': 'error', 'message': 'Key not found'}  # 处理未找到的键
        else:
            results[key] = response.json()  # 将响应结果存储到字典中
    return results  # 返回所有结果

def display_as_table(data):
    """ 以表格形式显示数据 """
    table = PrettyTable()
    table.field_names = ["Key", "Value", "Status"]  # 定义表格的列名
    
    # 设置对齐方式
    table.align["Key"] = "l"  # 左对齐
    table.align["Value"] = "l"  # 左对齐
    table.align["Status"] = "l"  # 左对齐

    for key, value in data.items():
        status = value.get('status', 'N/A')  # 获取状态，默认为 'N/A'
        if 'value' in value:
            table.add_row([key, value['value'], status])  # 添加行：包含键、值和状态
        else:
            table.add_row([key, '', status])  # 当没有值时，值列留空

    # 打印带颜色的表头
    header = Fore.CYAN + table.get_string() + Style.RESET_ALL
    print(header)  # 打印表格

def display_json(data):
    """ 以 JSON 格式显示数据 """
    print(json.dumps(data, indent=4))  # 将数据格式化为 JSON 字符串并打印

def usage():
    """ 显示用法说明 """
    print(Fore.YELLOW + "用法说明:" + Style.RESET_ALL)
    print("python client.py <action> <key> [<value>] [--json] [--table]")
    print("\n操作类型:")
    print("  put     : 添加一个或多个键值对 (格式: key1=value1,key2=value2)")
    print("  get     : 获取一个或多个键的值 (格式: key1,key2)")
    print("  delete  : 删除一个或多个键 (格式: key1,key2)")
    print("\n选项:")
    print("  --json  : 以 JSON 格式输出结果")
    print("  --table : 以表格格式输出结果")
    print(Fore.RED + "\n错误: 输入参数不正确，请参考用法说明。" + Style.RESET_ALL)

if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Client for HTTP K-V store')
    parser.add_argument('action', choices=['put', 'get', 'delete'], help='Action to perform')  # 操作类型
    parser.add_argument('key', help='Key to operate on or comma-separated keys for batch operations')  # 键或键列表
    parser.add_argument('value', nargs='?', help='Value to store (only needed for put, as key=value pairs)')  # 值（仅在 put 时需要）
    parser.add_argument('--json', action='store_true', help='Display output in JSON format')  # JSON 格式输出参数
    parser.add_argument('--table', action='store_true', help='Display output in table format')  # 表格格式输出参数

    # 尝试解析命令行参数
    try:
        args = parser.parse_args()  # 解析命令行参数
        
        # 检查输入参数是否符合要求
        if args.action == 'put':
            if args.key is None or '=' not in args.key:
                print(Fore.RED + "错误: 'put' 操作需要提供 key=value 对。" + Style.RESET_ALL)  # 错误提示
                usage()  # 显示用法说明
                exit(1)
            else:
                keys_values = {}
                pairs = args.key.split(',')  # 按逗号分割键值对
                for pair in pairs:
                    if '=' not in pair:
                        print(Fore.RED + f"错误: '{pair}' 不是有效的 key=value 对。" + Style.RESET_ALL)
                        usage()
                        exit(1)
                    key, value = pair.split('=', 1)  # 只分割第一个等号
                    keys_values[key.strip()] = value.strip()  # 去除空格并存入字典
                result = put(keys_values)  # 调用批量 put 函数
                if args.json:
                    display_json(result)  # 如果指定 JSON 格式，调用 JSON 输出
                elif args.table:
                    display_as_table(result)  # 如果指定表格格式，调用表格输出
                else:
                    for key in keys_values.keys():
                        print(Fore.GREEN + result[key]['status'] + Style.RESET_ALL)  # 添加颜色

        elif args.action == 'get':
            keys = args.key.split(',')  # 支持批量获取，将输入的键分割成列表
            result = get(keys)  # 调用批量 get 函数
            if args.json:
                display_json(result)  # 如果指定 JSON 格式，调用 JSON 输出
            elif args.table:
                display_as_table(result)  # 如果指定表格格式，调用表格输出
            else:
                for key in keys:
                    if key in result and 'value' in result[key]:
                        print(Fore.BLUE + f"{key}: {result[key]['value']}" + Style.RESET_ALL)  # 添加颜色
                    else:
                        print(Fore.RED + f"{key}: {result[key]['status']}" + Style.RESET_ALL)  # 添加颜色

        elif args.action == 'delete':
            keys = args.key.split(',')  # 支持批量删除，将输入的键分割成列表
            result = delete(keys)  # 调用批量 delete 函数
            if args.json:
                display_json(result)  # 如果指定 JSON 格式，调用 JSON 输出
            elif args.table:
                display_as_table(result)  # 如果指定表格格式，调用表格输出
            else:
                for key in keys:
                    print(Fore.YELLOW + result[key]['status'] + Style.RESET_ALL)  # 添加颜色

    except SystemExit:
        # 捕获 SystemExit 异常以显示用法说明
        usage()
    except Exception as e:
        print(Fore.RED + f"错误: {str(e)}" + Style.RESET_ALL)  # 捕获异常并打印错误信息
        usage()  # 显示用法说明
        exit(1)  # 退出程序


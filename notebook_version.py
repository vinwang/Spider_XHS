"""
小红书笔记爬虫 - 魔塔社区Notebook版本
=====================================

功能：
- 搜索并爬取小红书高互动笔记
- 支持按点赞数、收藏数筛选
- 自动保存为Excel格式

使用前准备：
1. 确保已配置Cookie（见下方配置）
2. 安装依赖：pip install -r requirements.txt
3. 运行代码块

注意：
- Cookie可能会过期，需要定期更新
- 请勿过于频繁请求，遵守平台规则
- 仅供学习研究使用
"""

# @title 🔧 配置区域 - 请填写你的Cookie
# @markdown > 获取Cookie方法：登录小红书后，按F12打开开发者工具，在Network标签页找到请求的Cookie

COOKIE = ""  # @param {type:"string"}

# @title 📊 爬取参数设置
# @markdown 设置搜索关键词和筛选条件

QUERY = "ai提示词"  # @param {type:"string"}
QUERY_NUM = 30  # @param {type:"integer", min:1, max:200}
MIN_LIKES = 1000  # @param {type:"integer", min:0}
MIN_COLLECTS = 2000  # @param {type:"integer", min:0}
SORT_TYPE = "最多点赞"  # @param ["综合排序", "最新", "最多点赞", "最多评论", "最多收藏"]
NOTE_TYPE = "不限"  # @param ["不限", "视频笔记", "普通笔记"]
SAVE_CHOICE = "只保存Excel"  # @param ["只保存Excel", "只保存媒体文件", "保存所有（Excel+媒体）"]

def install_dependencies():
    """安装必要的依赖包"""
    import subprocess
    import sys
    
    packages = [
        'requests',
        'loguru', 
        'python-dotenv',
        'retry',
        'openpyxl',
        'PyExecJS'
    ]
    
    print("📦 正在安装依赖包...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
            print(f"  ✅ {package}")
        except Exception as e:
            print(f"  ⚠️ {package} 安装失败: {e}")
    
    print("✨ 依赖安装完成！\n")


def init():
    """初始化爬虫环境"""
    import os
    
    # 设置保存路径
    base_path = {
        'excel': os.path.abspath('datas/excel_datas'),
        'media': os.path.abspath('datas/media_datas')
    }
    
    # 创建目录
    for path in base_path.values():
        os.makedirs(path, exist_ok=True)
    
    return COOKIE, base_path


def parse_number(num_str):
    """
    将字符串格式的数字转换为整数，如 '2.7万' -> 27000
    """
    if isinstance(num_str, int):
        return num_str
    elif isinstance(num_str, str):
        num_str = num_str.strip()
        if '万' in num_str:
            try:
                return int(float(num_str.replace('万', '')) * 10000)
            except ValueError:
                return 0
        elif '千' in num_str:
            try:
                return int(float(num_str.replace('千', '')) * 1000)
            except ValueError:
                return 0
        else:
            try:
                return int(num_str)
            except ValueError:
                return 0
    else:
        return 0


def handle_note_info(data):
    """处理笔记信息"""
    import time
    
    def timestamp_to_str(timestamp):
        time_local = time.localtime(timestamp / 1000)
        return time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    
    try:
        note_type = data['note_card']['type']
        if note_type == 'normal':
            note_type = '图集'
        else:
            note_type = '视频'
        
        # 解析互动数据
        liked_count = parse_number(data['note_card']['interact_info']['liked_count'])
        collected_count = parse_number(data['note_card']['interact_info']['collected_count'])
        comment_count = parse_number(data['note_card']['interact_info']['comment_count'])
        share_count = parse_number(data['note_card']['interact_info']['share_count'])
        
        # 处理图片列表
        image_list_temp = data['note_card']['image_list']
        image_list = []
        for image in image_list_temp:
            try:
                image_list.append(image['info_list'][1]['url'])
            except:
                pass
        
        # 处理视频信息
        video_cover = None
        video_addr = None
        if note_type == '视频':
            try:
                if image_list:
                    video_cover = image_list[0]
                if 'video' in data['note_card'] and 'consumer' in data['note_card']['video']:
                    video_addr = 'https://sns-video-bd.xhscdn.com/' + data['note_card']['video']['consumer']['origin_video_key']
            except:
                pass
        
        # 处理标签
        tags_temp = data['note_card']['tag_list']
        tags = [tag['name'] for tag in tags_temp if 'name' in tag]
        
        # IP归属地
        ip_location = data['note_card'].get('ip_location', '未知')
        
        return {
            'note_id': data['id'],
            'note_url': data['url'],
            'note_type': note_type,
            'user_id': data['note_card']['user']['user_id'],
            'home_url': f"https://www.xiaohongshu.com/user/profile/{data['note_card']['user']['user_id']}",
            'nickname': data['note_card']['user']['nickname'],
            'avatar': data['note_card']['user']['avatar'],
            'title': data['note_card']['title'].strip() or '无标题',
            'desc': data['note_card']['desc'],
            'liked_count': liked_count,
            'collected_count': collected_count,
            'comment_count': comment_count,
            'share_count': share_count,
            'video_cover': video_cover,
            'video_addr': video_addr,
            'image_list': image_list,
            'tags': tags,
            'upload_time': timestamp_to_str(data['note_card']['time']),
            'ip_location': ip_location,
        }
    except Exception as e:
        print(f"处理笔记信息失败: {e}")
        return None


def save_to_xlsx(datas, file_path, search_query=''):
    """保存数据到Excel"""
    import openpyxl
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # 设置表头
    headers = [
        '搜索词', '标题', '描述', '标签', '点赞数量', '收藏数量', 
        '评论数量', '分享数量', '笔记url', '笔记id', '用户id', 
        '用户主页url', '昵称', '头像url', '图片地址url列表', 
        '视频封面url', '视频地址url', '上传时间', 'ip归属地'
    ]
    ws.append(headers)
    
    # 写入数据
    for data in datas:
        row_data = [
            search_query,
            data.get('title', ''),
            data.get('desc', ''),
            str(data.get('tags', [])),
            data.get('liked_count', 0),
            data.get('collected_count', 0),
            data.get('comment_count', 0),
            data.get('share_count', 0),
            data.get('note_url', ''),
            data.get('note_id', ''),
            data.get('user_id', ''),
            data.get('home_url', ''),
            data.get('nickname', ''),
            data.get('avatar', ''),
            str(data.get('image_list', [])),
            data.get('video_cover', ''),
            data.get('video_addr', ''),
            data.get('upload_time', ''),
            data.get('ip_location', ''),
        ]
        ws.append(row_data)
    
    wb.save(file_path)
    print(f"💾 数据已保存到: {file_path}")


def get_note_info(note_url, cookies_str):
    """获取单条笔记详情"""
    import urllib.parse
    import requests
    import json
    import time
    
    def generate_x_b3_traceid(length=16):
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def get_common_headers():
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }
    
    def splice_str(api, params):
        if params:
            query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
            return f"{api}?{query_string}"
        return api
    
    def generate_request_params(cookies_str, api, data, method='GET'):
        import execjs
        import random
        
        headers = get_common_headers()
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['Content-Type'] = 'application/json'
        
        # 读取xs文件
        try:
            with open('static/xs-common-1128.js', 'r', encoding='utf-8') as f:
                xs_code = f.read()
            
            # 读取x-s文件
            with open('static/xhs_xray.js', 'r', encoding='utf-8') as f:
                x_s_code = f.read()
            
            # 编译JS代码
            xs_compiled = execjs.compile(xs_code)
            x_s_compiled = execjs.compile(x_s_code)
            
            # 获取x_s值
            x_s = x_s_compiled.call('get_x_s', api, json.dumps(data) if data else '', method)
            
            # 获取xs值
            ctx = execjs.compile(xs_code + '\n' + x_s_code)
            xs_value = ctx.call('getXs', api, '2.0', x_s, '0')
            
            cookies = {}
            if cookies_str:
                for item in cookies_str.split(';'):
                    if '=' in item:
                        key, value = item.strip().split('=', 1)
                        cookies[key.strip()] = value.strip()
            
            # 构建headers
            headers['x_s'] = x_s
            headers['x_t'] = str(int(time.time() * 1000))
            headers['x_trace_id'] = generate_x_b3_traceid()
            headers['xs'] = xs_value
            
            return headers, cookies, json.dumps(data) if data else ''
            
        except Exception as e:
            print(f"生成请求参数失败: {e}")
            return get_common_headers(), {}, ''
    
    try:
        urlParse = urllib.parse.urlparse(note_url)
        note_id = urlParse.path.split("/")[-1]
        kvs = urlParse.query.split('&')
        kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
        
        api = "/api/sns/web/v1/feed"
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": "1"},
            "xsec_source": kvDist.get('xsec_source', "pc_search"),
            "xsec_token": kvDist.get('xsec_token', '')
        }
        
        headers, cookies, post_data = generate_request_params(cookies_str, api, data, 'POST')
        
        response = requests.post(
            'https://edith.xiaohongshu.com' + api,
            headers=headers,
            data=post_data,
            cookies=cookies,
            timeout=10
        )
        
        result = response.json()
        
        if result.get('success') and result.get('data', {}).get('items'):
            note_data = result['data']['items'][0]
            note_data['url'] = note_url
            return True, "成功", note_data
        else:
            return False, f"获取失败: {result.get('msg', '未知错误')}", None
            
    except Exception as e:
        return False, str(e), None


def search_notes(query, require_num, cookies_str, sort_type_choice, note_type):
    """搜索笔记"""
    import urllib.parse
    import requests
    import json
    import time
    
    def generate_x_b3_traceid(length=16):
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def get_common_headers():
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
        }
    
    def splice_str(api, params):
        if params:
            query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
            return f"{api}?{query_string}"
        return api
    
    def generate_request_params(cookies_str, api, data, method='GET'):
        import execjs
        import random
        
        headers = get_common_headers()
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['Content-Type'] = 'application/json'
        
        try:
            with open('static/xs-common-1128.js', 'r', encoding='utf-8') as f:
                xs_code = f.read()
            
            with open('static/xhs_xray.js', 'r', encoding='utf-8') as f:
                x_s_code = f.read()
            
            xs_compiled = execjs.compile(xs_code)
            x_s_compiled = execjs.compile(x_s_code)
            
            x_s = x_s_compiled.call('get_x_s', api, json.dumps(data) if data else '', method)
            
            ctx = execjs.compile(xs_code + '\n' + x_s_code)
            xs_value = ctx.call('getXs', api, '2.0', x_s, '0')
            
            cookies = {}
            if cookies_str:
                for item in cookies_str.split(';'):
                    if '=' in item:
                        key, value = item.strip().split('=', 1)
                        cookies[key.strip()] = value.strip()
            
            headers['x_s'] = x_s
            headers['x_t'] = str(int(time.time() * 1000))
            headers['x_trace_id'] = generate_x_b3_traceid()
            headers['xs'] = xs_value
            
            return headers, cookies, json.dumps(data) if data else ''
            
        except Exception as e:
            print(f"生成请求参数失败: {e}")
            return get_common_headers(), {}, ''
    
    # 转换排序参数
    sort_map = {
        "综合排序": 0,
        "最新": 1,
        "最多点赞": 2,
        "最多评论": 3,
        "最多收藏": 4
    }
    
    note_type_map = {
        "不限": 0,
        "视频笔记": 1,
        "普通笔记": 2
    }
    
    sort_type = "general"
    if sort_type_choice == 1:
        sort_type = "time_descending"
    elif sort_type_choice == 2:
        sort_type = "popularity_descending"
    elif sort_type_choice == 3:
        sort_type = "comment_descending"
    elif sort_type_choice == 4:
        sort_type = "collect_descending"
    
    filter_note_type = "不限"
    if note_type == 1:
        filter_note_type = "视频笔记"
    elif note_type == 2:
        filter_note_type = "普通笔记"
    
    page = 1
    note_list = []
    
    try:
        while len(note_list) < require_num:
            api = "/api/sns/web/v1/search/notes"
            data = {
                "keyword": query,
                "page": page,
                "page_size": 20,
                "search_id": generate_x_b3_traceid(21),
                "sort": sort_type,
                "note_type": 0,
                "ext_flags": [],
                "filters": [
                    {"tags": [sort_type], "type": "sort_type"},
                    {"tags": [filter_note_type], "type": "filter_note_type"},
                    {"tags": ["不限"], "type": "filter_note_time"},
                    {"tags": ["不限"], "type": "filter_note_range"},
                    {"tags": ["不限"], "type": "filter_pos_distance"}
                ],
                "geo": "",
                "image_formats": ["jpg", "webp", "avif"]
            }
            
            headers, cookies, post_data = generate_request_params(cookies_str, api, data, 'POST')
            
            response = requests.post(
                'https://edith.xiaohongshu.com' + api,
                headers=headers,
                data=post_data.encode('utf-8'),
                cookies=cookies,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success') and result.get('data', {}).get('items'):
                notes = result['data']['items']
                note_list.extend(notes)
                page += 1
                
                if not result['data'].get('has_more'):
                    break
            else:
                print(f"搜索失败: {result.get('msg', '未知错误')}")
                break
            
            # 避免请求过快
            time.sleep(1)
        
        return True, "搜索成功", note_list[:require_num]
        
    except Exception as e:
        return False, str(e), None


def crawl_xiaohongshu():
    """主爬取函数"""
    import os
    from datetime import datetime
    
    print("=" * 60)
    print("🚀 小红书笔记爬虫 - 魔塔社区Notebook版本")
    print("=" * 60)
    print(f"📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 搜索关键词: {QUERY}")
    print(f"📊 搜索数量: {QUERY_NUM}")
    print(f"👍 最低点赞: {MIN_LIKES}")
    print(f"⭐ 最低收藏: {MIN_COLLECTS}")
    print("-" * 60)
    
    # 验证Cookie
    if not COOKIE:
        print("❌ 错误: 请先配置Cookie！")
        print("📝 获取方法:")
        print("  1. 登录小红书网站")
        print("  2. 按F12打开开发者工具")
        print("  3. 切换到Network标签")
        print("  4. 刷新页面，找到请求的Cookie")
        print("  5. 复制完整的Cookie字符串")
        return
    
    # 初始化
    print("🔧 初始化中...")
    cookies_str, base_path = init()
    print("✅ 初始化完成！\n")
    
    # 搜索笔记
    print(f"🔍 开始搜索 '{QUERY}' ...")
    
    # 转换参数
    sort_map = {"综合排序": 0, "最新": 1, "最多点赞": 2, "最多评论": 3, "最多收藏": 4}
    note_type_map = {"不限": 0, "视频笔记": 1, "普通笔记": 2}
    
    success, msg, notes = search_notes(
        QUERY, QUERY_NUM, COOKIE,
        sort_map.get(SORT_TYPE, 2),
        note_type_map.get(NOTE_TYPE, 0)
    )
    
    if not success or not notes:
        print(f"❌ 搜索失败: {msg}")
        return
    
    print(f"✅ 搜索到 {len(notes)} 条笔记\n")
    
    # 过滤笔记
    notes = [n for n in notes if n.get('model_type') == 'note']
    print(f"📋 有效笔记数量: {len(notes)}\n")
    
    # 爬取笔记详情
    print("📥 开始爬取笔记详情...")
    filtered_notes = []
    total = len(notes)
    
    for i, note in enumerate(notes, 1):
        print(f"  进度: {i}/{total} ({int(i/total*100)}%)", end='\r')
        
        note_url = f"https://www.xiaohongshu.com/explore/{note['id']}?xsec_token={note['xsec_token']}"
        success, msg, note_info = get_note_info(note_url, COOKIE)
        
        if success and note_info:
            note_info = handle_note_info(note_info)
            if note_info:
                # 筛选高互动笔记
                if (note_info['liked_count'] > MIN_LIKES or 
                    note_info['collected_count'] > MIN_COLLECTS):
                    filtered_notes.append(note_info)
        
        # 避免请求过快
        time.sleep(0.5)
    
    print(f"\n✅ 爬取完成！")
    print(f"📊 原始笔记数量: {total}")
    print(f"✨ 符合条件数量: {len(filtered_notes)}\n")
    
    if not filtered_notes:
        print("⚠️ 没有找到符合条件的笔记")
        print("💡 建议: 降低筛选条件（点赞数或收藏数）")
        return
    
    # 保存结果
    print("💾 保存数据中...")
    
    # 转换保存选项
    save_map = {
        "只保存Excel": "excel",
        "只保存媒体文件": "media", 
        "保存所有（Excel+媒体）": "all"
    }
    
    save_choice = save_map.get(SAVE_CHOICE, 'excel')
    
    # 生成文件名
    filename = f"{QUERY}_{len(filtered_notes)}条笔记"
    excel_path = os.path.join(base_path['excel'], f"{filename}.xlsx")
    
    # 保存Excel
    save_to_xlsx(filtered_notes, excel_path, QUERY)
    
    print("\n" + "=" * 60)
    print("🎉 爬取完成！")
    print("=" * 60)
    print(f"📁 Excel文件: {excel_path}")
    print(f"📊 符合条件笔记: {len(filtered_notes)} 条")
    print("-" * 60)
    
    # 显示前几条数据预览
    print("\n📋 数据预览（前3条）:")
    for i, note in enumerate(filtered_notes[:3], 1):
        print(f"  {i}. {note['title'][:30]}...")
        print(f"     👍 {note['liked_count']}  ⭐ {note['collected_count']}")
    
    print("\n💡 提示:")
    print("  - Excel文件已保存，可以下载到本地")
    print("  - Cookie可能会过期，需要定期更新")
    print("  - 请勿过于频繁请求")
    print("=" * 60)


if __name__ == "__main__":
    # 安装依赖
    install_dependencies()
    
    # 运行爬虫
    crawl_xiaohongshu()

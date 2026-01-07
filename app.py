from flask import Flask, render_template, request, jsonify, send_from_directory
from main import Data_Spider
from xhs_utils.common_util import init
import threading
import time
import os

app = Flask(__name__)

# 初始化爬虫
cookies_str, base_path = init()
data_spider = Data_Spider()

# 爬取状态管理
crawl_status = {
    'is_running': False,
    'progress': 0,
    'message': '等待开始',
    'result': None
}


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/crawl', methods=['POST'])
def crawl():
    """开始爬取"""
    global crawl_status
    
    if crawl_status['is_running']:
        return jsonify({
            'success': False,
            'message': '爬取任务正在运行中，请稍后再试'
        })
    
    # 获取请求参数
    query = request.form.get('query', '榴莲')
    query_num = int(request.form.get('query_num', 50))
    min_likes = int(request.form.get('min_likes', 1000))
    min_collects = int(request.form.get('min_collects', 2000))
    sort_type_choice = int(request.form.get('sort_type', 2))
    note_type = int(request.form.get('note_type', 0))
    save_choice = request.form.get('save_choice', 'excel')
    
    # 重置爬取状态
    crawl_status = {
        'is_running': True,
        'progress': 0,
        'message': '开始爬取...',
        'result': None
    }
    
    # 启动爬取线程
    def crawl_thread():
        global crawl_status
        try:
            # 调用爬虫函数
            note_list, success, msg = data_spider.spider_some_search_note(
                query=query,
                require_num=query_num,
                cookies_str=cookies_str,
                base_path=base_path,
                save_choice=save_choice,
                sort_type_choice=sort_type_choice,
                note_type=note_type,
                min_likes=min_likes,
                min_collects=min_collects
            )
            
            # 更新爬取状态
            crawl_status['is_running'] = False
            crawl_status['progress'] = 100
            crawl_status['message'] = '爬取完成'
            crawl_status['result'] = {
                'success': success,
                'message': msg,
                'total_notes': len(note_list),
                'excel_path': os.path.abspath(os.path.join(base_path['excel'], f'{query}.xlsx'))
            }
        except Exception as e:
            # 更新错误状态
            crawl_status['is_running'] = False
            crawl_status['progress'] = 100
            crawl_status['message'] = f'爬取失败: {str(e)}'
            crawl_status['result'] = {
                'success': False,
                'message': str(e)
            }
    
    threading.Thread(target=crawl_thread).start()
    
    return jsonify({
        'success': True,
        'message': '爬取任务已启动'
    })


@app.route('/status')
def get_status():
    """获取爬取状态"""
    return jsonify(crawl_status)


@app.route('/download/<filename>')
def download_file(filename):
    """下载Excel文件"""
    excel_path = os.path.abspath(os.path.join(base_path['excel'], filename))
    if os.path.exists(excel_path):
        return send_from_directory(os.path.dirname(excel_path), filename, as_attachment=True)
    else:
        return jsonify({'success': False, 'message': '文件不存在'})


if __name__ == '__main__':
    # 创建templates目录
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 使用waitress作为WSGI服务器，提供更好的稳定性
    from waitress import serve
    print('服务已启动，访问地址: http://localhost:5000')
    serve(app, host='0.0.0.0', port=5000)
# 方法二：requests + BeautifulSoup4
# 与 scrapy_douban_by_xpath.py（Selenium+XPath版）字段、数据库结构完全一致，
from bs4 import BeautifulSoup
import requests
import hashlib
import re
import csv
import time
import pymysql
from db_config import DB_CONFIG  # 数据库配置从 .env 读取，源码不硬编码
url = "https://movie.douban.com/top250"
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
    'Referer': 'https://movie.douban.com/top250'
}
FIELDS = ['title', 'year', 'rank', 'directors', 'screenwriters', 'actors', 'genres', 'country', 'language',
          'release_date', 'runtime', 'aka', 'rating', 'votes', 'star_5', 'star_4', 'star_3', 'star_2', 'star_1', 'summary']

# 拿到标签对应的内容，主要用来提取导演那些数据的（和XPath版同一个思路）
def get_value(label, lines):
    for line in lines:
        if line.startswith(label):
            return line[len(label):].strip().lstrip(':').strip()
    return ''

# 用同一个会话发请求，保住过关后发的 Cookie
session = requests.Session()
session.headers.update(headers)


# 破解风控挑战：算最小的 nonce 使 sha512(cha+nonce) 的十六进制前 4 位都是 0
# （豆瓣的挑战页就是让浏览器用 JS 算这个"工作量证明"，Python 用 hashlib 照做即可）
def solve_pow(cha, difficulty=4):
    target = '0' * difficulty
    nonce = 0
    while True:
        nonce += 1
        if hashlib.sha512((cha + str(nonce)).encode()).hexdigest().startswith(target):
            return nonce


# 用 requests 拿页面源码；命中风控挑战页就本地算 sol 提交过关，再重取页面
def get_html(page_url):
    for i in range(5):
        resp = session.get(page_url, timeout=15)
        resp.encoding = 'utf-8'
        html = resp.text
        # 正常列表页有 grid_view；正常详情页有 content 和 rating_per
        if ('id="content"' in html and 'rating_per' in html) or 'grid_view' in html:
            return html
        # 命中"载入中..."挑战页：提取表单参数 -> 算出 sol -> 提交 -> 拿回真页面
        if 'id="tok"' in html:
            soup = BeautifulSoup(html, 'html.parser')
            tok = soup.find(attrs={'id': 'tok'})['value']
            cha = soup.find(attrs={'id': 'cha'})['value']
            red = soup.find(attrs={'id': 'red'})['value']
            sol = str(solve_pow(cha))
            print(f'  命中风控挑战，已算出 sol={sol}，提交过关...')
            resp = session.post('https://sec.douban.com/c',
                                data={'tok': tok, 'cha': cha, 'sol': sol, 'red': red},
                                timeout=15)
            resp.encoding = 'utf-8'
            html = resp.text
            if ('id="content"' in html and 'rating_per' in html) or 'grid_view' in html:
                return html
        print(f'  疑似触发反爬，第 {i + 1} 次重试...')
        time.sleep(2)
    return html


# 解析列表页，返回本页 25 部电影的详情页 url（bs4 的 select 用法）
def parse_list(html):
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    for li in soup.select('div.article ol li'):
        a = li.select_one('div.hd a')
        if a:
            urls.append(a['href'])
    return urls


# 解析详情页，把所有字段包装成字典（bs4 的 find / select 用法）
def parse_detail(html):
    soup = BeautifulSoup(html, 'html.parser')

    # 电影的名字、评分、投票数等信息
    title = soup.select_one('h1 span[property="v:itemreviewed"]')
    year = soup.select_one('h1 span.year')
    rating = soup.select_one('strong.ll.rating_num')
    votes = soup.select_one('span[property="v:votes"]')
    rank = soup.select_one('span.top250-no')

    # 星级占比，把他们按键值对的方式提取出来
    stars = {}
    for it in soup.select('div.ratings-on-weight div.item'):
        star_name = it.find('span', attrs={'title': True})
        per = it.select_one('span.rating_per')
        if star_name and per:
            # str() 显式转换：bs4 新版的属性值类型标注是 list|str，转成字符串
            # 才能安全地当字典 key 用（消除 PyCharm 的 unhashable type 告警）
            star_title = str(star_name.get('title', ''))
            name_map = {'力荐': '5星', '推荐': '4星', '还行': '3星', '较差': '2星', '很差': '1星'}
            stars[name_map.get(star_title, star_title)] = per.get_text().strip()

    # 剧情简介：完整版藏在 class="all hidden" 里，没有就退回短简介
    full = soup.select_one('span.all.hidden') or soup.select_one('span[property="v:summary"]')
    summary = ''
    if full:
        summary = ' '.join(t.strip() for t in full.get_text().split('\n') if t.strip())
        summary = summary.replace('©豆瓣', '').strip()

    # 导演演员等信息：把 #info 里的 <br> 换成换行符，再按行拆开
    lines = []
    info_div = soup.find('div', id='info')
    if info_div:
        for br in info_div.find_all('br'):
            br.replace_with('\n')
        lines = [line.strip() for line in info_div.get_text().split('\n') if line.strip()]

    info = {
        'title': title.get_text().strip() if title else '',
        'year': year.get_text().strip('()') if year else '',
        'rank': rank.get_text().strip() if rank else '',
        'directors': get_value('导演', lines),
        'screenwriters': get_value('编剧', lines),
        'actors': get_value('主演', lines),
        'genres': get_value('类型', lines),
        'country': get_value('制片国家/地区', lines),
        'language': get_value('语言', lines),
        'release_date': get_value('上映日期', lines),
        'runtime': get_value('片长', lines),
        'aka': get_value('又名', lines),
        'rating': rating.get_text().strip() if rating else '',
        'votes': votes.get_text().strip() if votes else '',
        'star_5': stars.get('5星', ''),
        'star_4': stars.get('4星', ''),
        'star_3': stars.get('3星', ''),
        'star_2': stars.get('2星', ''),
        'star_1': stars.get('1星', ''),
        'summary': summary
    }
    return info
# 存储到csv中
def save_csv(movies):
    with open("E:/PythonProject2/考核/实战一：豆瓣爬虫/douban_top250_bs4.csv", 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    print(f'\nCSV 保存完成，共 {len(movies)} 条')

# 存储到数据库中
def save_mysql(movies):
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS douban_top250_bs4 (
        id INT AUTO_INCREMENT PRIMARY KEY,
        `rank` INT, title VARCHAR(300), year VARCHAR(20),
        directors VARCHAR(500), screenwriters VARCHAR(500), actors VARCHAR(1000),
        genres VARCHAR(200), country VARCHAR(200), language VARCHAR(200),
        release_date VARCHAR(300), runtime VARCHAR(100), aka VARCHAR(500),
        rating DECIMAL(3,1), votes VARCHAR(50),
        star_5 VARCHAR(10), star_4 VARCHAR(10), star_3 VARCHAR(10),
        star_2 VARCHAR(10), star_1 VARCHAR(10),
        summary TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # 字段名统一加反引号，避免 rank 等保留字导致语法错误
    sql = f"INSERT INTO douban_top250_bs4 ({','.join('`' + f + '`' for f in FIELDS)}) " \
          f"VALUES ({','.join(['%s'] * len(FIELDS))})"
    for m in movies:
        row = [m.get(f, '') for f in FIELDS]
        # rank 原值是 'No.243' 这类带前缀字符串，清洗成整数（如 243）再入库
        if 'rank' in FIELDS:
            idx = FIELDS.index('rank')
            row[idx] = int(re.sub(r'\D', '', str(row[idx])) or 0)
        # rating 为空串时传 None，避免 DECIMAL 列插入空串报错
        if 'rating' in FIELDS:
            idx = FIELDS.index('rating')
            row[idx] = float(row[idx]) if row[idx] else None
        # votes 清洗成整数
        if 'votes' in FIELDS:
            idx = FIELDS.index('votes')
            row[idx] = int(re.sub(r'\D', '', str(row[idx])) or 0) if row[idx] else 0
        cur.execute(sql, row)
    conn.commit()
    cur.close()
    conn.close()
    print(f'MySQL 保存完成：spider.douban_top250_bs4，共 {len(movies)} 条')


if __name__ == '__main__':
    movies = []
    # 1.经过抓取每一页的url后找出规律
    for page in range(0, 250, 25):
        page_href = url + f'?start={page}&filter='
        # 2.用 requests 打开列表页，bs4 解析出每个电影的详情页链接
        movie_urls = parse_list(get_html(page_href))
        print(f'第 {page // 25 + 1} 页，共解析出 {len(movie_urls)} 个详情页')
        for movie_href in movie_urls:
            # 3.用 bs4 解析详情页，提取全部字段
            info = parse_detail(get_html(movie_href))
            print(info)
            movies.append(info)
            time.sleep(1)
    # 4.以csv的形式存入
    save_csv(movies)
    # 5.存入数据库
    save_mysql(movies)

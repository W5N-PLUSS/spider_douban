from my_utils import get_browser
from selenium.webdriver.common.by import By
from lxml import etree
import time
import re
import csv
import pymysql
from db_config import DB_CONFIG
# 经过一开始的尝试发现有反爬,加入Uer-Agent之后就好了
url="https://movie.douban.com/top250"
headers={

'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
'cookie':
'll="118099"; bid=AlY1oHqptC0; _vwo_uuid_v2=DDF62CFFA3E5523AC1A012C5D34F93AC3|b42db2a154c96774f3a12b88dca4e488; __utmz=30149280.1788871146.6.3.utmcsr=sec.douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/; ap_v=0,6.0; __utma=30149280.876145087.1783645737.1791457319.1791544160.8; __utmb=30149280.0.10.1791544160; __utmc=30149280; dbsawcv1=MTc5MTU0Njc4OUBlNzY0MGRiMWMzOTQ1NjQ2YzAwOGVjZTViNGYxYTdkMjJhYThhYTQyYmM2ZmE1N2VjNWFhYTI3NzkyOTAwMDBlQDNhYWY5ODBkYWE3Yzk2N2ZAYWQzYjYwNTRjZWU0',
'Referer':'https://movie.douban.com/top250'
}

# 数据库配置统一从 db_config.DB_CONFIG 读取（凭据走 .env，不硬编码）
# 用selenium拿到具体每个电影详情页
def get_detail_html(web, movie_url):
    web.get(movie_url)
    # 如果碰到反爬的 loading 页，就多等一会儿再刷新，最多等 20 秒
    for i in range(10):
        m_content = web.page_source
        if 'id="content"' in m_content and 'rating_per' in m_content:
            return m_content
        if '点我继续浏览' in m_content:  # 爬取过程中发现会弹出这个验证，单独处理一下
            try:
                btn = web.find_element(By.XPATH, '//*[contains(text(), "点我继续浏览")]')
                btn.click()
            except Exception:
                pass
        time.sleep(2)
    return web.page_source

# 拿到标签对应的内容，主要用来提取导演那些数据的
def get_value(label,lines):
    for line in lines:
        if line.startswith(label):
            return line[len(label):].strip().lstrip(':').strip()
    return ''


# 用 Selenium 打开列表页
def get_list_html(web, page_url):
    web.get(page_url)
    html = web.page_source
    if '点我继续浏览' in html:
        try:
            btn = web.find_element(By.XPATH, '//*[contains(text(), "点我继续浏览")]')
            btn.click()
            time.sleep(3)
            html = web.page_source
        except Exception:
            pass
    return html

# 存储到csv中
FIELDS = ['title','year','rank','directors','screenwriters','actors','genres','country','language',
'release_date','runtime','aka','rating','votes','star_5','star_4','star_3','star_2','star_1','summary']
def save_csv(movies):
    with open("douban_top250.csv", 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    print(f'\nCSV 保存完成，共 {len(movies)} 条')

# 存储到数据库中
def save_mysql(movies):
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    # 以和下方 FIELDS 完全对齐（表当前为空，无数据损失）
    # cur.execute('DROP TABLE IF EXISTS douban_top250')
    cur.execute('''CREATE TABLE IF NOT EXISTS douban_top250 (
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
    sql = f"INSERT INTO douban_top250 ({','.join('`'+f+'`' for f in FIELDS)}) " \
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
        # votes 清洗成整数（去掉可能的非数字字符）
        if 'votes' in FIELDS:
            idx = FIELDS.index('votes')
            row[idx] = int(re.sub(r'\D', '', str(row[idx])) or 0) if row[idx] else 0
        cur.execute(sql, row)
    conn.commit()
    cur.close()
    conn.close()
    print(f'MySQL 保存完成：spider.douban_top250，共 {len(movies)} 条')

if __name__ == '__main__':
    web=get_browser()
    movies=[]
    # 1.经过抓取每一页的url后找出规律
    for page in range(0,250,25):
        page_href=url+f'?start={page}&filter='
        # 2. 用 Selenium 打开列表页并取源码
        page_html = etree.HTML(get_list_html(web, page_href))
        # 3.找到每一个电影的具体页面
        lis=page_html.xpath('//div[@class="article"]//li')
        for li in lis:
            # 电影的名字评分投票数等信息
            movie_href=li.xpath('./div/div[2]/div[1]/a/@href')
            movie_text=get_detail_html(web,movie_href[0])
            movie_html=etree.HTML(movie_text)
            rank=movie_html.xpath('//div[@id="content"]//span[@class="top250-no"]/text()')
            title=movie_html.xpath('//h1/span[1]/text()')
            year = movie_html.xpath('//h1/span[@class="year"]/text()')
            rating = movie_html.xpath('//strong[@class="ll rating_num"]/text()')
            votes = movie_html.xpath('//span[@property="v:votes"]/text()')
            # 星级占比,把他们按键值对的方式提取出来
            stars = {}
            for it in movie_html.xpath('//div[@class="ratings-on-weight"]//div[@class="item"]'):
                star_name = it.xpath('.//span/@title')
                per = it.xpath('./span[@class="rating_per"]/text()')
                if star_name and per:
                    name_map = {'力荐': '5星', '推荐': '4星', '还行': '3星', '较差': '2星', '很差': '1星'}
                    stars[name_map.get(star_name[0], star_name[0])] = per[0].strip()
            full = movie_html.xpath('//span[@class="all hidden"]//text()')
            if not full:
                full = movie_html.xpath('//span[@property="v:summary"]//text()')
            summary = ' '.join(t.strip() for t in full if t.strip()).replace('©豆瓣', '').strip()

            # 导演演员等信息
            info_node = movie_html.xpath('//div[@id="info"]')
            lines = []
            if info_node:
                # etree.tostring : 把info_node[0]重新序列化回HTML字符串
                inner = etree.tostring(info_node[0], encoding='unicode')
                for seg in re.split(r'<br\s*/?>', inner):
                    frag = etree.HTML(f'<div>{seg}</div>')
                    text = ' '.join(frag.itertext()).split()
                    text = ' '.join(text)
                    if text:
                        lines.append(text)
            # 4.将电影的所有信息都包装成字典提取到info里面
            info={
                'title':title[0].strip() if title else '',
                'year':year[0].strip('()') if year else '',
                'rank': rank[0].strip() if rank else '',
                'directors': get_value('导演',lines),
                'screenwriters': get_value('编剧',lines),
                'actors': get_value('主演',lines),
                'genres': get_value('类型',lines),
                'country': get_value('制片国家/地区',lines),
                'language': get_value('语言',lines),
                'release_date': get_value('上映日期',lines),
                'runtime': get_value('片长',lines),
                'aka': get_value('又名',lines),
                'rating': rating[0] if rating else '',
                'votes': votes[0] if votes else '',
                'star_5': stars.get('5星', ''),
                'star_4': stars.get('4星', ''),
                'star_3': stars.get('3星', ''),
                'star_2': stars.get('2星', ''),
                'star_1': stars.get('1星', ''),
                'summary': summary
            }
            print(info)
            movies.append(info)
            time.sleep(1)
    web.quit()
    # 5.以csv的形式存入
    save_csv(movies)
    # 6.存入数据库
    save_mysql(movies)





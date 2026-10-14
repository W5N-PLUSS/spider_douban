# 实战一：豆瓣电影 Top250 爬虫

使用两种方案抓取豆瓣电影 Top250，并写入阿里云 RDS（MySQL）：

- **bs4 版** `douban_top250_by_bs4.py`：requests + BeautifulSoup 解析页面
- **XPath / Selenium 版** `scrapy_douban_by_xpath.py`：Selenium 驱动浏览器 + lxml 的 XPath 解析（更适合有反爬 / 动态渲染的页面）

两个版本共用 `db_config.py`（读取数据库配置）与 `my_utils.py`（提供 `get_browser()`）。

## 功能
- 抓取 Top250 电影：排名、片名、年份、导演、编剧、主演、类型、国家、语言、上映日期、片长、又名、评分、评价人数、星级占比、简介
- 自动 `CREATE TABLE IF NOT EXISTS douban_top250`
- 同时输出 CSV 样例：`douban_top250.csv`（XPath 版产物）、`douban_top250_bs4.csv`（bs4 版产物）

## 依赖
```bash
pip install -r requirements.txt
```

## 配置（重要）
数据库凭据从 `.env` 读取，源码不硬编码。
1. 复制 `.env.example` 为 `.env`
2. 填入 `DB_*` 真实信息
3. 运行：`python douban_top250_by_bs4.py` 或 `python scrapy_douban_by_xpath.py`

> 注意：`.env` 含真实凭据，切勿手动 `git add .env`。

## 目录
- `douban_top250_by_bs4.py` 主程序（bs4 版）
- `scrapy_douban_by_xpath.py` 主程序（XPath / Selenium 版）
- `db_config.py` 数据库连接配置（读 `.env`，两个版本共用）
- `my_utils.py` 工具模块（提供 `get_browser()`，两个版本共用）
- `douban_top250.csv` / `douban_top250_bs4.csv` 抓取结果样例

## 说明
- 数据库表名 `douban_top250`，脚本自动建表，无需手动建。
- `my_utils.py` 中 Chrome / chromedriver 路径为本机绝对路径，换机运行需按本机环境修改。
- 反爬相关设置（User-Agent、Cookie、延时等）请按需调整。

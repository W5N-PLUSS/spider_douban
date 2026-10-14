# 实战一：豆瓣电影 Top250 爬虫（bs4 版）

使用 requests + BeautifulSoup 抓取豆瓣电影 Top250，写入阿里云 RDS（MySQL）。

## 功能
- 请求豆瓣 Top250 页面，解析电影条目
- BeautifulSoup 提取排名、片名、评分、评价人数、引言等
- PyMySQL 落库，自动 `CREATE TABLE IF NOT EXISTS`
- 输出 `douban_top250_bs4.csv` 作为数据样例

## 依赖
```bash
pip install -r requirements.txt
```

## 配置（重要）
数据库凭据从 `.env` 读取，源码不硬编码。
1. 复制 `.env.example` 为 `.env`
2. 填入 `DB_*` 真实信息
3. `python douban_top250_by_bs4.py`

> 注意：`.env` 含真实凭据，切勿手动 `git add .env`。

## 目录
- `douban_top250_by_bs4.py` 主程序（bs4 版）
- `db_config.py` 数据库连接配置（读 `.env`，各版本共用）
- `douban_top250.csv` / `douban_top250_bs4.csv` 抓取结果样例
- `scrapy_douban_by_xpath.py` 未包含（Scrapy 框架版，按需求排除）

## 说明
- 数据库表名 `douban_top250`，脚本自动建表，无需手动建。
- 反爬相关设置请按需调整。

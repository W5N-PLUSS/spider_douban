# -*- coding: utf-8 -*-
"""
MySQL 连接配置（阿里云 RDS）—— bs4 版和 Scrapy 版共用
真实凭据从项目根目录的 .env 读取（已在 .gitignore 中忽略），请勿硬编码。
两个版本写入同一张表，用 method 字段（bs4 / scrapy）区分，不会互相覆盖。
"""
import os

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "your-rds-host.mysql.rds.aliyuncs.com"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "your_user"),
    "password": os.getenv("DB_PASSWORD", "your_password"),
    "database": os.getenv("DB_NAME", "your_database"),
    "charset":  "utf8mb4",
}

# 数据表名（不需要提前建表，脚本会自动 CREATE TABLE IF NOT EXISTS）
TABLE_NAME = "douban_top250"

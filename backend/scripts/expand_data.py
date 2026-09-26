"""扩展数据到500+资产"""
import sqlite3
import json
import random

random.seed(42)
conn = sqlite3.connect('./backend/financesim.db')
cur = conn.cursor()

# 美股
us_stocks = [
    ('AAPL.OQ', 'Apple', 'Technology', 'Consumer Electronics', 195.0),
    ('MSFT.OQ', 'Microsoft', 'Technology', 'Software', 380.0),
    ('GOOGL.OQ', 'Alphabet', 'Technology', 'Internet', 140.0),
    ('AMZN.OQ', 'Amazon', 'Technology', 'E-commerce', 178.0),
    ('TSLA.OQ', 'Tesla', 'Automotive', 'EV', 245.0),
    ('NVDA.OQ', 'NVIDIA', 'Technology', 'Semiconductors', 875.0),
    ('META.OQ', 'Meta', 'Technology', 'Social Media', 500.0),
    ('NFLX.OQ', 'Netflix', 'Media', 'Streaming', 480.0),
    ('AMD.OQ', 'AMD', 'Technology', 'Semiconductors', 165.0),
    ('INTC.OQ', 'Intel', 'Technology', 'Semiconductors', 42.0),
    ('CRM.N', 'Salesforce', 'Technology', 'Software', 270.0),
    ('ADBE.N', 'Adobe', 'Technology', 'Software', 520.0),
    ('AVGO.OQ', 'Broadcom', 'Technology', 'Semiconductors', 1350.0),
    ('COST.N', 'Costco', 'Consumer', 'Retail', 680.0),
    ('DIS.N', 'Disney', 'Media', 'Entertainment', 110.0),
    ('JNJ.N', 'Johnson & Johnson', 'Healthcare', 'Pharma', 155.0),
    ('KO.N', 'Coca-Cola', 'Consumer', 'Beverages', 60.0),
    ('MCD.N', 'McDonald\'s', 'Consumer', 'Restaurants', 295.0),
    ('MMM.N', '3M', 'Industrial', 'Conglomerate', 105.0),
    ('NKE.N', 'Nike', 'Consumer', 'Apparel', 105.0),
    ('PFE.N', 'Pfizer', 'Healthcare', 'Pharma', 28.0),
    ('WMT.N', 'Walmart', 'Consumer', 'Retail', 165.0),
    ('XOM.N', 'ExxonMobil', 'Energy', 'Oil', 105.0),
    ('CVX.N', 'Chevron', 'Energy', 'Oil', 155.0),
    ('JPM.N', 'JPMorgan', 'Financial', 'Banking', 195.0),
    ('BAC.N', 'Bank of America', 'Financial', 'Banking', 33.0),
    ('GS.N', 'Goldman Sachs', 'Financial', 'Investment', 420.0),
    ('V.N', 'Visa', 'Financial', 'Payments', 270.0),
    ('MA.N', 'Mastercard', 'Financial', 'Payments', 420.0),
    ('PYPL.N', 'PayPal', 'Financial', 'Payments', 65.0),
]

# A股
a_stocks = [
    ('600519.SH', '贵州茅台', 'Consumer', 'Liquor', 1680.0),
    ('000858.SZ', '五粮液', 'Consumer', 'Liquor', 145.0),
    ('000568.SZ', '泸州老窖', 'Consumer', 'Liquor', 185.0),
    ('603288.SH', '海天味业', 'Consumer', 'Food', 45.0),
    ('002304.SZ', '洋河股份', 'Consumer', 'Liquor', 95.0),
    ('600887.SH', '伊利股份', 'Consumer', 'Dairy', 28.0),
    ('002714.SZ', '牧原股份', 'Consumer', 'Pork', 38.0),
    ('002415.SZ', '海康威视', 'Tech', 'Security', 32.0),
    ('300750.SZ', '宁德时代', 'Tech', 'Battery', 185.0),
    ('002475.SZ', '立讯精密', 'Tech', 'Electronics', 38.0),
    ('688111.SH', '金山办公', 'Tech', 'Software', 285.0),
    ('300059.SZ', '东方财富', 'Tech', 'Fintech', 22.0),
    ('600276.SH', '恒瑞医药', 'Healthcare', 'Pharma', 42.0),
    ('300124.SZ', '汇川技术', 'Tech', 'Industrial Automation', 68.0),
    ('002594.SZ', '比亚迪', 'Auto', 'EV', 245.0),
    ('601012.SH', '隆基绿能', 'Tech', 'Solar', 25.0),
    ('000725.SZ', '京东方A', 'Tech', 'Display', 4.20),
    ('601899.SH', '紫金矿业', 'Energy', 'Mining', 15.0),
    ('600900.SH', '长江电力', 'Energy', 'Hydro', 28.0),
    ('600036.SH', '招商银行', 'Finance', 'Banking', 35.0),
    ('601166.SH', '兴业银行', 'Finance', 'Banking', 22.0),
    ('601818.SH', '光大银行', 'Finance', 'Banking', 3.80),
    ('601939.SH', '建设银行', 'Finance', 'Banking', 6.20),
    ('601288.SH', '农业银行', 'Finance', 'Banking', 3.90),
    ('601988.SH', '中国银行', 'Finance', 'Banking', 3.80),
    ('000001.SZ', '平安银行', 'Finance', 'Banking', 11.0),
    ('000002.SZ', '万科A', 'Real Estate', 'Residential', 12.0),
    ('601318.SH', '中国平安', 'Finance', 'Insurance', 48.0),
    ('601601.SH', '中国太保', 'Finance', 'Insurance', 28.0),
    ('600030.SH', '中信证券', 'Finance', 'Brokerage', 22.0),
    ('601688.SH', '华泰证券', 'Finance', 'Brokerage', 18.0),
    ('600837.SH', '海通证券', 'Finance', 'Brokerage', 8.50),
    ('600000.SH', '浦发银行', 'Finance', 'Banking', 9.50),
    ('600009.SH', '上海机场', 'Transport', 'Airport', 32.0),
    ('600011.SH', '华能国际', 'Energy', 'Power', 7.20),
    ('600015.SH', '华夏银行', 'Finance', 'Banking', 5.80),
    ('600016.SH', '民生银行', 'Finance', 'Banking', 4.20),
    ('600018.SH', '上港集团', 'Transport', 'Port', 4.50),
    ('600019.SH', '宝钢股份', 'Steel', 'Steel', 6.80),
    ('600028.SH', '中国石化', 'Energy', 'Oil', 6.50),
    ('600029.SH', '南方航空', 'Transport', 'Airline', 6.80),
    ('600031.SH', '三一重工', 'Industrial', 'Machinery', 18.0),
]

# ETF
etfs = [
    ('510300.SH', '沪深300ETF', 'Index', 'Broad Market', 4.20),
    ('510500.SH', '中证500ETF', 'Index', 'Mid Cap', 6.50),
    ('510050.SH', '上证50ETF', 'Index', 'Large Cap', 3.10),
    ('159915.SZ', '创业板ETF', 'Index', 'Growth', 2.15),
    ('512880.SH', '证券公司ETF', 'Index', 'Finance', 1.05),
    ('512660.SH', '军工ETF', 'Index', 'Defense', 0.85),
    ('512760.SH', '医药ETF', 'Index', 'Healthcare', 0.92),
    ('515030.SH', '新能源ETF', 'Index', 'New Energy', 1.15),
    ('512480.SH', '半导体ETF', 'Index', 'Semiconductor', 1.35),
    ('512690.SH', '酒ETF', 'Index', 'Consumer', 1.65),
    ('512180.SH', '计算机ETF', 'Index', 'Tech', 0.88),
    ('515050.SH', '通信ETF', 'Index', 'Telecom', 0.75),
]

added = 0

# Insert US stocks
for ticker, name, sector, industry, price in us_stocks:
    cur.execute('SELECT 1 FROM assets WHERE ticker=?', (ticker,))
    if not cur.fetchone():
        try:
            cur.execute('''INSERT INTO assets 
                (world_id, ticker, type, name, exchange, sector, industry, currency, market_cap, beta, volatility, fundamentals, current_price)
                VALUES (1, ?, 'EQUITY', ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?, ?)''',
                (ticker, name, 'NASDAQ', sector, industry, 
                 round(price * 100, 2), round(random.uniform(0.8, 1.8), 2),
                 round(random.uniform(0.20, 0.50), 2),
                 json.dumps({'pe': round(random.uniform(15, 40), 1), 'pb': round(random.uniform(2.0, 6.0), 2)}),
                 price))
            added += 1
        except Exception as e:
            print(f'Error {ticker}: {e}')

# Insert A-shares
for ticker, name, sector, industry, price in a_stocks:
    cur.execute('SELECT 1 FROM assets WHERE ticker=?', (ticker,))
    if not cur.fetchone():
        try:
            cur.execute('''INSERT INTO assets 
                (world_id, ticker, type, name, exchange, sector, industry, currency, market_cap, beta, volatility, fundamentals, current_price)
                VALUES (1, ?, 'EQUITY', ?, ?, ?, ?, ?, 'CNY', ?, ?, ?, ?, ?)''',
                (ticker, name, 'SSE', sector, industry,
                 round(price * 50, 2), round(random.uniform(0.6, 1.5), 2),
                 round(random.uniform(0.18, 0.35), 2),
                 json.dumps({'pe': round(random.uniform(10, 40), 1), 'pb': round(random.uniform(1.0, 4.0), 2)}),
                 price))
            added += 1
        except Exception as e:
            print(f'Error {ticker}: {e}')

# Insert ETFs
for ticker, name, sector, industry, price in etfs:
    cur.execute('SELECT 1 FROM assets WHERE ticker=?', (ticker,))
    if not cur.fetchone():
        try:
            cur.execute('''INSERT INTO assets 
                (world_id, ticker, type, name, exchange, sector, industry, currency, market_cap, beta, volatility, fundamentals, current_price)
                VALUES (1, ?, 'ETF', ?, ?, ?, ?, 'CNY', 500, ?, ?, '{}', ?)''',
                (ticker, name, 'SSE', sector, industry,
                 round(random.uniform(0.8, 1.5), 2),
                 round(random.uniform(0.15, 0.30), 2),
                 price))
            added += 1
        except Exception as e:
            print(f'Error {ticker}: {e}')

conn.commit()

cur.execute('SELECT COUNT(*) FROM assets')
total = cur.fetchone()[0]
print(f'Added {added} new assets')
print(f'Total assets: {total}')

cur.execute('SELECT type, COUNT(*) FROM assets GROUP BY type')
print('\nDistribution:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

cur.execute('SELECT COUNT(*) FROM assets WHERE current_price IS NOT NULL')
with_price = cur.fetchone()[0]
print(f'\nWith price: {with_price}/{total} ({with_price/total*100:.1f}%)')

conn.close()

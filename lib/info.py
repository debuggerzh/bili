critical_cookie = {
    'DedeUserID': '12696567',
    'SESSDATA': 'b3381589%2C1699592988%2C377cf%2A52',
    'bili_jct': '537db12561485d8eb0d9c73ee3bf552b'
}
date_headers = {
    "referer": "https://www.bilibili.com/",
    "origin": "https://www.bilibili.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66 "
}
user_headers = {'authority': 'api.bilibili.com',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
                'accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip'}

username = "zcfcferw"
password = "2ivraqs8"
proxy_ip = '116.62.70.158:16819'
kuai_proxies = {
    "http": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": username, "pwd": password, "proxy": proxy_ip},
    "https": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": username, "pwd": password, "proxy": proxy_ip}
}

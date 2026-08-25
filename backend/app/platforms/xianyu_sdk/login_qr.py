"""闲鱼扫码登录 → 二维码保存为图片 → 手机扫图片"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import qrcode
from goofish_apis import build_initial_cookies
from utils.goofish_utils import get_session_cookies_str
import requests, time

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 1. 拿基础cookie
print('获取基础cookie...')
s = build_initial_cookies()
s.headers.update({'User-Agent': UA, 'Referer': 'https://www.goofish.com/'})

# 2. 加载passport
s.get('https://passport.goofish.com/mini_login.htm', 
    params={'lang':'zh_cn','appName':'xianyu','appEntrance':'web','styleType':'vertical','bizParams':'','notLoadSsoView':'false','notKeepLogin':'false','isMobile':'false','qrCodeFirst':'false','stie':'77','rnd':'0.5'})

# 3. 生成二维码
print('生成二维码...')
for attempt in range(3):
    r = s.post('https://passport.goofish.com/qrcodeGenerate.do', data={'lgToken':'generate'})
    try:
        token = r.json()['lgToken']
        break
    except:
        print(f'  重试 {attempt+1}...')
        time.sleep(2)
else:
    print('生成失败')
    sys.exit(1)

qr_url = f'https://passport.goofish.com/qrcodeCheck.htm?lgToken={token}&_from=havana'
img = qrcode.make(qr_url)
imgpath = os.path.expanduser('~/桌面/xianyu_qr.png')
img.save(imgpath)
print(f'\n✅ 二维码已保存: {imgpath}')
print(f'📱 打开桌面的 xianyu_qr.png，用闲鱼App扫描')
print(f'⏳ 等待扫码...\n')

# 4. 轮询
for i in range(60):
    time.sleep(2)
    r = s.get('https://passport.goofish.com/qrcodeQuery.do', params={'lgToken':token,'isSdk':'false'})
    try:
        d = r.json()
        st = d.get('status','')
        tip = d.get('tip', '')
        if tip: print(f'  [{i*2}s] {tip}')
        if st in ('SUCCESS','HOLDER'):
            cookies_str = get_session_cookies_str(s)
            unb = s.cookies.get('unb', '')
            print(f'\n========== 登录成功！==========')
            print(f'Cookie长度: {len(cookies_str)}')
            print(f'\nCookie（复制到设置页第一栏）:\n{cookies_str}')
            print(f'\nunb: {unb}')
            sys.exit(0)
    except:
        pass

print('\n超时，重试')

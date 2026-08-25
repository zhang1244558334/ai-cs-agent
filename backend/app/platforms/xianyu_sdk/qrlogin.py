"""闲鱼扫码登录 - 大尺寸二维码版本"""
import qrcode, requests, time, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.goofish_utils import get_session_cookies_str
from goofish_apis import build_initial_cookies
from urllib.parse import quote

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
s = build_initial_cookies()
cna = s.cookies.get('cna', domain='.goofish.com') or s.cookies.get('cna', domain='.mmstat.com') or ''
cookie2 = s.cookies.get('cookie2', domain='.goofish.com') or ''

s.headers.update({'User-Agent': UA, 'Referer': 'https://www.goofish.com/'})
s.get('https://passport.goofish.com/mini_login.htm',
    params={'lang':'zh_cn','appName':'xianyu','appEntrance':'web','styleType':'vertical','bizParams':'','notLoadSsoView':'false','notKeepLogin':'false','isMobile':'false','qrCodeFirst':'false'})

csrf = s.cookies.get('_csrf_token','')
r = s.post('https://passport.goofish.com/newlogin/qrcode/generate.do',
    data={'appName':'xianyu','fromSite':'77','appEntrance':'web','_csrf_token':csrf,'umidToken':'','hsiz':cookie2,
          'bizParams':'taobaoBizLoginFrom=web','mainPage':'false','isMobile':'false','lang':'zh_CN',
          'returnUrl':'','umidTag':'SERVER','navlanguage':'en','navUserAgent':UA,'navPlatform':'Win32',
          'isIframe':'true','documentReferer':'https://www.goofish.com/','defaultView':'sms','deviceId':cna})
gen = r.json()
qr_url = gen.get('url') or gen.get('codeContent','')
qr_t = gen.get('t','')

img = qrcode.make(qr_url)
img = img.resize((400,400))
img.save(os.path.join(os.path.expanduser('~'), '桌面', 'xianyu_qr_big.png'))
print(f'打开桌面 xianyu_qr_big.png，用闲鱼App扫')

deadline = time.time() + 120
last = ''
while time.time() < deadline:
    time.sleep(2)
    r2 = s.post('https://passport.goofish.com/newlogin/qrcode/query.do',
        data={'appName':'xianyu','fromSite':'77','appEntrance':'web','_csrf_token':csrf,'umidToken':'',
              'hsiz':cookie2,'bizParams':f'taobaoBizLoginFrom=web&renderRefer={quote("https://www.goofish.com/")}',
              'mainPage':'false','isMobile':'false','lang':'zh_CN','returnUrl':'','umidTag':'SERVER',
              'navlanguage':'en','navUserAgent':UA,'navPlatform':'Win32','isIframe':'true',
              'documentReferer':'https://www.goofish.com/','defaultView':'sms','deviceId':cna,
              'lgToken':gen.get('lgToken',''),'t':qr_t,'ck':gen.get('ck','')})
    d = r2.json()
    st = d.get('status','')
    if st != last:
        print(f'[{st}] {d.get("tip",st)} ({int(deadline-time.time())}s)')
        last = st
    if st == 'CONFIRMED':
        login_token = d.get('token') or d.get('lgToken')
        s.post('https://passport.goofish.com/login_token/login.do',
            params={'token':login_token,'subFlow':'DIALOG_CHECK_LOGIN_RPC','nextCode':'0018','bizScene':'qrcode','confirm':'true'},
            data={'deviceId':cna})
        cookie_str = get_session_cookies_str(s)
        unb = s.cookies.get('unb','')
        print(f'\n✅ 成功！Cookie:{len(cookie_str)}字 unb:{unb}')
        with open(os.path.join(os.path.expanduser('~'), '桌面', 'xianyu_cookie.txt'),'w') as f: f.write(cookie_str)
        with open(os.path.join(PROJECT_ROOT, 'config', 'settings.json')) as f: d2 = json.load(f)
        d2['platform_config'] = json.dumps({'app_key':cookie_str,'seller_id':unb})
        with open(os.path.join(PROJECT_ROOT, 'config', 'settings.json'),'w') as f: json.dump(d2,f,ensure_ascii=False,indent=2)
        print('已保存！')
        sys.exit(0)
    elif st == 'EXPIRED':
        print('过期')
        sys.exit(1)
print('超时')

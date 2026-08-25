"""一键闲鱼登录：生成QR图→用户扫码→自动保存Cookie"""
import qrcode, requests, time, json, sys, os, shutil
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))
from utils.goofish_utils import get_session_cookies_str
from goofish_apis import build_initial_cookies

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
s = build_initial_cookies()
cna = s.cookies.get('cna', domain='.goofish.com') or s.cookies.get('cna', domain='.mmstat.com') or ''
cookie2 = s.cookies.get('cookie2', domain='.goofish.com') or ''
s.headers.update({'User-Agent': UA, 'Referer': 'https://www.goofish.com/'})

# 1. mini_login
s.get('https://passport.goofish.com/mini_login.htm',
    params={'lang':'zh_cn','appName':'xianyu','appEntrance':'web','styleType':'vertical',
            'bizParams':'','notLoadSsoView':'false','notKeepLogin':'false','isMobile':'false','qrCodeFirst':'false'})

# 2. 生成二维码
csrf = s.cookies.get('_csrf_token','')
r = s.post('https://passport.goofish.com/newlogin/qrcode/generate.do',
    data={'appName':'xianyu','fromSite':'77','appEntrance':'web','_csrf_token':csrf,
          'umidToken':'','hsiz':cookie2,'bizParams':'taobaoBizLoginFrom=web',
          'mainPage':'false','isMobile':'false','lang':'zh_CN','returnUrl':'',
          'umidTag':'SERVER','navlanguage':'en','navUserAgent':UA,'navPlatform':'Win32',
          'isIframe':'true','documentReferer':'https://www.goofish.com/',
          'defaultView':'sms','deviceId':cna})
gen = r.json()
qr_url = gen.get('codeContent','')
lg_token = gen.get('lgToken','')
qr_t = gen.get('t','')
qr_ck = gen.get('ck','')

# 3. 保存QR图片
img = qrcode.make(qr_url)
img.save('/tmp/xy_qr.png')
shutil.copy('/tmp/xy_qr.png', os.path.join(os.path.expanduser('~'), '桌面', 'xy_qr.png'))
print(f'✅ QR图片: 桌面/xy_qr.png')
print(f'📱 打开图片，用闲鱼App扫！')
print(f'⏳ 等待扫码...')

# 4. 轮询
biz = f'taobaoBizLoginFrom=web&renderRefer={quote("https://www.goofish.com/")}'
deadline = time.time() + 180
last = ''
while time.time() < deadline:
    time.sleep(2)
    r2 = s.post('https://passport.goofish.com/newlogin/qrcode/query.do',
        data={'appName':'xianyu','fromSite':'77','appEntrance':'web','_csrf_token':csrf,
              'umidToken':'','hsiz':cookie2,'bizParams':biz,'mainPage':'false',
              'isMobile':'false','lang':'zh_CN','returnUrl':'','umidTag':'SERVER',
              'navlanguage':'en','navUserAgent':UA,'navPlatform':'Win32','isIframe':'true',
              'documentReferer':'https://www.goofish.com/','defaultView':'sms',
              'deviceId':cna,'lgToken':lg_token,'t':qr_t,'ck':qr_ck})
    try:
        d = r2.json()
    except:
        continue
    st = d.get('status','')
    if st != last:
        remaining = int(deadline - time.time())
        print(f'  [{st}] {d.get("tip",st)} ({remaining}s)')
        last = st
    if st == 'CONFIRMED':
        token = d.get('token') or d.get('lgToken')
        s.post('https://passport.goofish.com/login_token/login.do',
            params={'token':token,'subFlow':'DIALOG_CHECK_LOGIN_RPC','nextCode':'0018',
                    'bizScene':'qrcode','confirm':'true'}, data={'deviceId':cna})
        cookie_str = get_session_cookies_str(s)
        unb = s.cookies.get('unb','')
        print(f'\n✅ 登录成功！Cookie长度:{len(cookie_str)} unb:{unb}')

        with open(os.path.join(os.path.expanduser('~'), '桌面', 'cookie_final.txt'),'w') as f: f.write(cookie_str)
        with open(os.path.join(PROJECT_ROOT, 'config', 'settings.json')) as f:
            settings = json.load(f)
        settings['platform_config'] = json.dumps({'app_key':cookie_str,'seller_id':unb})
        with open(os.path.join(PROJECT_ROOT, 'config', 'settings.json'),'w') as f:
            json.dump(settings,f,ensure_ascii=False,indent=2)
        print('已保存到设置！')
        sys.exit(0)
    elif st == 'EXPIRED':
        print('二维码过期，重试')
        sys.exit(1)

print('超时')

#!/usr/bin/env python3
"""修复Python 3.10 ctypes.util bug后再启动闲鱼Bot"""

import ctypes.util
import re

# Monkey-patch: 修复Python 3.10 ctypes.util._findSoname_ldconfig的bytes/string兼容bug
_original_findSoname_ldconfig = ctypes.util._findSoname_ldconfig if hasattr(ctypes.util, '_findSoname_ldconfig') else None

def _patched_findSoname_ldconfig(name):
    if _original_findSoname_ldconfig:
        try:
            return _original_findSoname_ldconfig(name)
        except TypeError:
            pass
    # 回退方案：手动查ldconfig
    import subprocess
    try:
        proc = subprocess.run(['ldconfig', '-p'], capture_output=True, text=True, timeout=5)
        regex = re.compile(r'\s+lib%s\.so(?:\.[0-9]+)*\s+\((.*)\)' % re.escape(name))
        for line in proc.stdout.splitlines():
            m = regex.search(line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

ctypes.util._findSoname_ldconfig = _patched_findSoname_ldconfig

# 现在安全导入并启动Bot
import json, asyncio, sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

with open(os.path.join(PROJECT_ROOT, 'config', 'settings.json')) as f:
    s = json.load(f)
cfg = json.loads(s.get('platform_config', '{}'))
cookies = cfg.get('app_key', '')
print(f'[Bot] Cookie: {len(cookies)}字节')

from backend.app.gateway.adapters.xianyu_bot import run_xianyu_bot
print('[Bot] 正在连接闲鱼WebSocket...')
asyncio.run(run_xianyu_bot(cookies))

# ⚠️ 纯加法改造，不删不改任何现有功能。电商业务一切照旧。

> 多业务线支持：在现有单租户框架上加业务切换，不改电商逻辑

# 项目上下文
- 现有路由：`backend/app/api/routes/knowledge.py` — upload/list/delete/search
- 现有知识库目录：`/home/a/桌面/ai-cs-agent/docs/` — 12个电商FAQ文件
- 现有前端：Vue 3 + Element Plus，`tenant_id=single` 写死在各处
- 前端 Knowledge.vue 已改造为表格+Tab布局
- 前端 App.vue 侧边栏有7个菜单项

# 改造内容

## 一、后端：新增业务线管理 API

### 新建文件：`backend/app/api/routes/business.py`

```python
import os
import json

from fastapi import APIRouter

router = APIRouter()

# 业务线配置文件
BUSINESS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "businesses.json")
DOCS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))


def _load_businesses() -> list[dict]:
    if not os.path.exists(BUSINESS_FILE):
        default = [{"id": "ecommerce", "name": "电商客服", "icon": "shopping-cart", "active": True}]
        os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
        with open(BUSINESS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(BUSINESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_businesses(data: list[dict]):
    os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
    with open(BUSINESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("/api/businesses")
async def list_businesses():
    return {"businesses": _load_businesses()}


@router.post("/api/businesses")
async def create_business(body: dict):
    """body: {name: str, icon: str}"""
    businesses = _load_businesses()
    bid = body["name"].lower().replace(" ", "_")
    if any(b["id"] == bid for b in businesses):
        from fastapi import HTTPException
        raise HTTPException(400, f"Business '{bid}' already exists")
    businesses.append({"id": bid, "name": body["name"], "icon": body.get("icon", "building-2"), "active": True})
    _save_businesses(businesses)
    return {"businesses": businesses}


@router.put("/api/businesses/{business_id}")
async def update_business(business_id: str, body: dict):
    businesses = _load_businesses()
    for b in businesses:
        if b["id"] == business_id:
            if "name" in body: b["name"] = body["name"]
            if "icon" in body: b["icon"] = body["icon"]
            if "active" in body: b["active"] = body["active"]
            _save_businesses(businesses)
            return {"businesses": businesses}
    from fastapi import HTTPException
    raise HTTPException(404, f"Business '{business_id}' not found")


@router.delete("/api/businesses/{business_id}")
async def delete_business(business_id: str):
    if business_id == "ecommerce":
        from fastapi import HTTPException
        raise HTTPException(400, "Cannot delete default ecommerce business")
    businesses = _load_businesses()
    businesses = [b for b in businesses if b["id"] != business_id]
    _save_businesses(businesses)
    return {"businesses": businesses}
```

### 注册路由：编辑 `backend/app/api/main.py` 或路由注册文件

找到现有的 `app.include_router(knowledge.router)` 那一行，在下面加：
```python
from app.api.routes import business
app.include_router(business.router)
```

## 二、后端：改造 knowledge.py 支持多业务目录隔离

### 修改 `backend/app/api/routes/knowledge.py`

**1. 改 DOCS_DIR 定义**（第12行）
```python
# 原来：
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))

# 改为：
DOCS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))
```

然后在 upload_doc、list_docs、delete_doc 三个函数开头，根据 tenant_id 计算子目录：
```python
tenant_dir = os.path.join(DOCS_BASE, tenant_id)
os.makedirs(tenant_dir, exist_ok=True)
```

**2. upload_doc：dest 路径改为子目录**
```python
# 原来第37行：
dest = os.path.join(DOCS_DIR, file.filename)
# 改为：
dest = os.path.join(tenant_dir, file.filename)
```

**3. list_docs：只返回当前业务的文档**
```python
# 原来（61-69行）：
@router.get("/api/knowledge")
async def list_docs():
    if not os.path.exists(DOCS_DIR):
        return {"documents": []}
    files = [f for f in os.listdir(DOCS_DIR) if f.endswith(...)]
    return {"documents": files}

# 改为：
@router.get("/api/knowledge")
async def list_docs(tenant_id: str = "ecommerce"):
    tenant_dir = os.path.join(DOCS_BASE, tenant_id)
    if not os.path.exists(tenant_dir):
        return {"documents": [], "tenant_id": tenant_id}
    files = [f for f in os.listdir(tenant_dir) if f.endswith((".md",".txt",".csv",".html",".pdf"))]
    return {"documents": files, "tenant_id": tenant_id}
```

**4. delete_doc：路径改为子目录**
```python
# 原来第74行：
filepath = os.path.join(DOCS_DIR, source)
# 改为：
tenant_dir = os.path.join(DOCS_BASE, tenant_id)  # 加 tenant_id 参数
filepath = os.path.join(tenant_dir, source)
```

**5. 迁移现有文件**
后端启动时（或独立脚本），把 `docs/` 下的12个电商.md文件移到 `docs/ecommerce/` 下。

创建脚本 `scripts/migrate_docs.py`：
```python
import os, shutil

DOCS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
ECOMMERCE = os.path.join(DOCS_BASE, "ecommerce")

os.makedirs(ECOMMERCE, exist_ok=True)
for f in os.listdir(DOCS_BASE):
    src = os.path.join(DOCS_BASE, f)
    dst = os.path.join(ECOMMERCE, f)
    if os.path.isfile(src) and not f.startswith("."):
        shutil.move(src, dst)
        print(f"  MOVED: {f} → ecommerce/")
print("Migration done.")
```

## 三、前端：业务切换器

### 改 App.vue

在 sidebar-header 下面、sidebar-nav 上面加业务选择器：

```html
<div class="business-switcher">
  <div class="business-current" @click="showBizSwitcher = !showBizSwitcher">
    <i :data-lucide="currentBiz.icon || 'shopping-cart'" class="biz-icon"></i>
    <span class="biz-name">{{ currentBiz.name }}</span>
    <i data-lucide="chevron-down" class="biz-arrow"></i>
  </div>
  <div v-if="showBizSwitcher" class="business-dropdown">
    <div v-for="biz in businesses" :key="biz.id"
         class="biz-option"
         :class="{ active: biz.id === activeBusiness }"
         @click="switchBusiness(biz)">
      <i :data-lucide="biz.icon || 'building-2'" class="biz-option-icon"></i>
      <span>{{ biz.name }}</span>
    </div>
    <div class="biz-divider"></div>
    <div class="biz-option biz-add" @click="showAddBiz = true">
      <i data-lucide="plus"></i> 新增业务
    </div>
  </div>
</div>
```

### Script 新增（追加，不改原有代码）

```javascript
const activeBusiness = ref('ecommerce')
const businesses = ref([{id:'ecommerce', name:'电商客服', icon:'shopping-cart'}])
const showBizSwitcher = ref(false)
const showAddBiz = ref(false)

const currentBiz = computed(() => 
  businesses.value.find(b => b.id === activeBusiness.value) || businesses.value[0]
)

async function loadBusinesses() {
  try {
    const r = await fetch('/api/businesses')
    const d = await r.json()
    businesses.value = d.businesses || []
  } catch(e) { /* keep default */ }
}

function switchBusiness(biz) {
  activeBusiness.value = biz.id
  showBizSwitcher.value = false
  // 刷新图标
  nextTick(() => { if (window.lucide) window.lucide.createIcons() })
}

// onMounted 里加 loadBusinesses()
```

### 侧边栏加「业务管理」菜单项（可选，方便在页面上增删业务）

在 menuItems 数组里加：
```javascript
{ path: '/business', label: '业务管理', icon: 'briefcase' },
```

## 四、前端 Knowledge.vue 改造

把写死的 `tenant_id=single` 改为从当前业务读取。

### Template 里上传 URL 改为：
```html
:action="`/api/knowledge?is_public=${isPublic}&tenant_id=${activeBusiness}`"
```

### list_docs 调用改为带 tenant_id：
```javascript
async function loadDocs() {
  const r = await fetch(`/api/knowledge?tenant_id=${activeBusiness}`)
  // ...
}
```

### 如何获取 activeBusiness？
通过 provide/inject 或直接读 localStorage。最简单：Knowledge.vue 里新增：
```javascript
// 从 localStorage 读取当前业务
const activeBusiness = computed(() => localStorage.getItem('activeBusiness') || 'ecommerce')
```

App.vue 的 switchBusiness 里写 `localStorage.setItem('activeBusiness', biz.id)`

## 实现顺序

1. 运行迁移脚本 `scripts/migrate_docs.py` — 把 docs/*.md → docs/ecommerce/*.md
2. 创建 `backend/app/api/routes/business.py`（以上完整代码）
3. 注册 business 路由
4. 改造 `knowledge.py` — DOCS_DIR → DOCS_BASE + tenant_dir
5. 改造 `knowledge.py` 的 list_docs 和 delete_doc 加 tenant_id 参数
6. 前端 App.vue — 加业务切换器
7. 前端 Knowledge.vue — 改 tenant_id 为动态
8. 创建 BusinessManager.vue 页面（业务增删改查）

## 关键规则
1. ⚠️ 不删不改电商的任何已有功能和数据
2. ⚠️ docs/ 目录结构改为 docs/{business}/，迁移脚本先行
3. ⚠️ 默认 business = "ecommerce"，向后兼容
4. 新增文件全部用 write_file 创建
5. 已有文件只改特定行，不改整个文件

# ⚠️ 只改前端 Vue 文件，不改后端！功能碰都不要碰！
# ⚠️ 只改 template 和 CSS，不改 script 里的业务逻辑

> 多业务线前端：侧边栏加业务切换器，Knowledge 加动态 tenant_id

# 项目上下文
- App.vue 已有 sidebar-header → sidebar-nav 结构
- Knowledge.vue 已改造为表格+Tab布局（482行）
- 后端已就绪：`/api/businesses` 返回业务列表，`/api/knowledge?tenant_id=ecommerce` 按业务隔离

# 改造一：App.vue — 侧边栏业务切换器

## 位置：sidebar-header 和 sidebar-nav 之间插入

```html
<div class="business-switcher">
  <div class="business-current" @click="showBizMenu = !showBizMenu">
    <i :data-lucide="currentBiz.icon || 'shopping-cart'" class="biz-icon"></i>
    <span class="biz-name">{{ currentBiz.name }}</span>
    <i data-lucide="chevron-down" class="biz-arrow"></i>
  </div>
  <div v-if="showBizMenu" class="business-menu">
    <div v-for="biz in filteredBusinesses" :key="biz.id"
         class="biz-option"
         :class="{ active: biz.id === activeBusiness }"
         @click="switchBusiness(biz)">
      <i :data-lucide="biz.icon || 'building-2'" class="biz-option-icon"></i>
      <span>{{ biz.name }}</span>
    </div>
    <div class="biz-divider"></div>
    <div class="biz-option biz-add" @click="addBusiness">
      <i data-lucide="plus"></i> 新增业务线
    </div>
  </div>
</div>
```

## Script 追加（加在现有 import/ref 后面，不删不改原有代码）

```javascript
// ===== 业务线管理（新增） =====
const activeBusiness = ref(localStorage.getItem('activeBusiness') || 'ecommerce')
const businesses = ref([])
const showBizMenu = ref(false)

const currentBiz = computed(() =>
  businesses.value.find(b => b.id === activeBusiness.value) || { id: 'ecommerce', name: '电商客服', icon: 'shopping-cart' }
)

const filteredBusinesses = computed(() =>
  businesses.value.filter(b => b.active !== false)
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
  localStorage.setItem('activeBusiness', biz.id)
  showBizMenu.value = false
  nextTick(() => { if (window.lucide) window.lucide.createIcons() })
}

function addBusiness() {
  const name = prompt('新业务线名称（如：金融客服）')
  if (!name) return
  fetch('/api/businesses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, icon: 'briefcase' }),
  }).then(r => r.json()).then(() => {
    loadBusinesses()
    showBizMenu.value = false
  })
}
```

在 onMounted 里加 `loadBusinesses()`。

## 需要处理点击外部关闭菜单：在 onMounted 里加

```javascript
document.addEventListener('click', (e) => {
  if (!e.target.closest('.business-switcher')) showBizMenu.value = false
})
```

## CSS（加在 App.vue 的 style 块末尾）

```css
.business-switcher { padding: 8px 12px; position: relative; }
.business-current {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border-radius: 6px; cursor: pointer; transition: background 0.2s;
}
.business-current:hover { background: rgba(79,195,247,0.08); }
.biz-icon { display: inline-flex; align-items: center; flex-shrink: 0; }
.biz-name { flex: 1; font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.8); }
.biz-arrow { display: inline-flex; align-items: center; color: rgba(255,255,255,0.3); font-size: 12px; }
.business-menu {
  position: absolute; left: 12px; right: 12px; top: 100%;
  background: #1e1e36; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
  padding: 4px; z-index: 100; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.biz-option {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border-radius: 6px; cursor: pointer; font-size: 13px; color: rgba(255,255,255,0.6);
  transition: all 0.15s;
}
.biz-option:hover { background: rgba(79,195,247,0.1); color: rgba(255,255,255,0.9); }
.biz-option.active { background: rgba(79,195,247,0.15); color: #4fc3f7; font-weight: 600; }
.biz-option-icon { display: inline-flex; align-items: center; flex-shrink: 0; }
.biz-divider { height: 1px; background: rgba(255,255,255,0.06); margin: 4px 8px; }
.biz-add { color: rgba(79,195,247,0.6); }
.biz-add:hover { color: #4fc3f7; }
```

# 改造二：Knowledge.vue — 动态 tenant_id

## 上传 URL 改动态（查找 `:action="`/api/knowledge`）

把：
```
:action="`/api/knowledge?is_public=${isPublic}&tenant_id=single`"
```
改成：
```
:action="`/api/knowledge?is_public=${isPublic}&tenant_id=${activeBiz}`"
```

## loadDocs 函数加 tenant_id 参数

```javascript
// 在 script 顶部加
const activeBiz = computed(() => localStorage.getItem('activeBusiness') || 'ecommerce')

// 修改 loadDocs（只改 fetch URL，不改其他逻辑）
async function loadDocs() {
  const r = await fetch(`/api/knowledge?tenant_id=${activeBiz.value}`)
  // 其余不变
}
```

## deleteDoc 的 fetch 也加上 tenant_id

```javascript
await fetch('/api/knowledge/' + encodeURIComponent(src) + '?tenant_id=' + activeBiz.value, { method: 'DELETE' })
```

# 改造三：Sessions.vue 和 Review.vue 等其他使用 tenant_id 的页面

搜索所有 `tenant_id=single` 或 `tenant_id: 'single'`，全部替换为从 localStorage 读取：
```javascript
const activeBiz = computed(() => localStorage.getItem('activeBusiness') || 'ecommerce')
```

然后在 URL 模板里用 `${activeBiz.value}` 替换 `single`。

# 关键规则
1. 只改 Vue 文件，不动 python 后端
2. 新增代码追加在原有代码后面
3. localStorage key 统一为 'activeBusiness'
4. 默认值统一为 'ecommerce'（向后兼容）
5. 原有 script 逻辑一行不删

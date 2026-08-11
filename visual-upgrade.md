# ⚠️ 警告：纯CSS视觉升级，不动任何JS逻辑、API调用、数据结构！只改 <style> 和 template 的结构包裹（不改数据绑定）

> 前端全面视觉美化升级。所有功能逻辑保持原样，只提升视觉效果。
> 已有文件：全部修改（但只改样式，不动功能）。

# 项目上下文
- 框架：Vue 3 + Element Plus + ECharts + Lucide 图标（unpkg CDN）
- 侧边栏：220px 宽，深色系，当前 #1a1a2e
- 内容区：flex:1，#f0f2f5 底色
- 卡片：白底 8px 圆角，box-shadow: 0 1px 2px rgba(0,0,0,0.06)
- Lucide 图标：data-lucide 属性，window.lucide.createIcons() 渲染
- 颜色主调：#1890ff（蓝）

# 全局视觉升级指令

## 1. App.vue — 侧边栏升级

### 配色改为渐变
- 侧边栏 background：linear-gradient(180deg, #0f0f23 0%, #1a1a2e 40%, #16213e 100%)
- 头部标题区：加一个 Lucide 图标（message-circle），字号加大到 18px，加 letter-spacing: 1px
- 头部下加一条微妙的渐变分割线：border-bottom: 1px solid rgba(255,255,255,0.06)

### 菜单项
- 默认色从 #999 改为 rgba(255,255,255,0.5)
- hover 背景：rgba(79,195,247,0.08)，左移 2px（transform: translateX(2px)），transition 0.2s
- active 状态：background: rgba(79,195,247,0.12)，左边框从 3px 改为 4px，颜色改为渐变色 #4fc3f7
- 图标和文字间距加大到 10px
- 选中项文字 color: #4fc3f7，字重 600

### 全局
- 所有过渡加 transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1)

## 2. Dashboard.vue — 仪表盘

### 统计卡片
- box-shadow 改为多层：0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)
- hover 时：transform: translateY(-2px)，box-shadow 加深到 0 8px 24px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06)
- transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1)
- 图标区域：border-radius 从 8px 加大到 12px，宽度高度从 44px 加大到 48px
- 图标颜色改为渐变背景：
  - health: background: linear-gradient(135deg, #f6ffed, #d9f7be)，color: #52c41a
  - primary: background: linear-gradient(135deg, #e6f7ff, #bae7ff)，color: #1890ff
  - warning: background: linear-gradient(135deg, #fff7e6, #ffe7ba)，color: #fa8c16
  - danger: background: linear-gradient(135deg, #fff2f0, #ffccc7)，color: #ff4d4f
- 数值字重 700，改为 #1a1a2e
- 标签颜色：#8c8c8c

### 图表卡片
- box-shadow 同统计卡片
- 图表标题下加一条 2px 的彩色短线（用 ::after 伪元素）：#1890ff
- 图表卡片 hover 微浮起同统计卡片

### 列表卡片（最近对话/最近提案）
- box-shadow 同统计卡片
- 标题加左侧 3px 装饰条（border-left），颜色 #1890ff，padding-left: 12px
- 表格行 hover: background: #fafafa → #f0f7ff
- 表头颜色从 #999 改为 #8c8c8c，字重 500

## 3. Chat.vue — 对话页

### 整体
- 聊天卡片 box-shadow 升级同统计卡片：0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)
- 头部加渐变底条：border-bottom: 2px solid #f0f0f0

### 聊天气泡
- 用户气泡：background: linear-gradient(135deg, #1890ff, #40a9ff)，加微阴影 box-shadow: 0 2px 6px rgba(24,144,255,0.2)
- AI 气泡：background: #f7f8fa，加微阴影 box-shadow: 0 1px 4px rgba(0,0,0,0.04)
- 气泡圆角加大到 16px（之前 12px）
- 气泡间距 16px → 20px
- 消息文字 line-height: 1.6（之前 1.5）

### 输入框区域
- footer 背景 #fafafa，上加 1px solid #f0f0f0
- 发送按钮从 40x40 改为 44x44，圆角 12px
- 输入框加 focus 时的 box-shadow 辉光：box-shadow: 0 0 0 2px rgba(24,144,255,0.15)

### 反馈按钮
- opacity 默认 0.3（之前 0.4），hover 0.9
- active 时加微阴影

### 正在输入动画
- 三个点颜色从 #bbb 改为 #bfbfbf，动画更流畅

### 「回到底部」按钮
- 改为半透明毛玻璃：background: rgba(255,255,255,0.9)，backdrop-filter: blur(8px)

## 4. Knowledge.vue — 知识库页

### 加白卡片包裹
- 整个页面内容包在一个白卡片 div 里
- 卡片样式：background #fff，border-radius 8px，padding 24px，box-shadow 同其他卡片
- 整个页面最大宽度 860px，居中

### 标题
- 用 h2.page-title（跟 Dashboard 一致）：font-size 20px，font-weight 600，color rgba(0,0,0,0.85)
- 加左侧装饰条（3px #1890ff）

### 上传结果预览区
- 绿色背景加圆角 8px

## 5. Review.vue — 审批页

### 加白卡片包裹
- 同 Knowledge，整个包白卡片，max-width 900px

### 标题
- h2.page-title 统一

### 审批卡片
- el-card 加 box-shadow 和 hover 微浮起
- 按钮组间距加大

## 6. Tenants.vue — 租户页

### 加白卡片包裹
- 同 Knowledge，max-width 1000px

### 标题
- h2.page-title 统一

## 7. TestCenter.vue — 测试中心

### 加白卡片包裹
- 同 Knowledge，max-width 1000px

### 标题
- h2.page-title 统一

## 关键规则（必须遵守）

1. ⚠️ 不动任何 JS 逻辑（script setup 里的代码一行不改）
2. ⚠️ 不动任何 API 调用、数据绑定、v-for、v-if
3. ⚠️ 不动任何 computed/watch/onMounted 等
4. 只改 <style> 块和 <template> 最外层的包裹结构（加个 div 包起来）
5. Lucide 图标渲染逻辑不动
6. ECharts 初始化和配置不动
7. Element Plus 组件属性不动
8. 所有颜色、阴影、过渡、圆角可以改
9. 所有 padding、margin、gap、font-size 可以调整

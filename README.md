---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'ccbbe7ff-bc70-4443-b8c1-05dae78c3307'
  PropagateID: 'ccbbe7ff-bc70-4443-b8c1-05dae78c3307'
  ReservedCode1: '40795f6d-65cb-43a1-a2db-72f58173377d'
  ReservedCode2: '40795f6d-65cb-43a1-a2db-72f58173377d'
---

# L3VPN 无损映射应用（C1 版 · 研究人员扩展 · Windows 绿色版）

> **版本说明**：C1 基于 C0 复制演进，新增**研究人员扩展功能**——模型 draft 上传、
> 模型特征解析展示、跨层级映射关系自定义。C0 原始代码保留在 workspace `C0/` 目录。

前后端一体打包：**后端**（FastAPI + 规则引擎 + YANG 校验）+ **前端**（映射可视化页面）。
本绿色版**已内置 Windows Python 3.11 运行时与全部依赖**，目标电脑**无需安装 Python、
无需安装任何依赖、无需联网**，解压后双击即可运行，像普通 Windows 应用一样使用。

## 目录结构

```
l3vpn-mapping-app/
├── start.bat           # 一键启动（Windows，双击即可）
├── start.sh            # 一键启动（Linux / macOS，需自备 Python）
├── app.py              # 后端入口（FastAPI：API + WebSocket + 前端托管）
├── draft_manager.py    # 【C1 新增】draft 上传 / 特征解析 / 映射定义 / 动态规则执行
├── engine/             # 映射规则引擎（45 条规则 + trace + 无损指标）
├── yang/               # YANG 资产（7 模块 + yang-library.json + drafts/ 上传目录）
├── mappings/           # 【C1 新增】研究人员定义的映射规则（dynamic-rules.json）
├── web/
│   └── lab-page1.html  # 前端页面（端口自适应 + 研究人员扩展 UI）
└── runtime/            # 【内置】Windows Python 3.11 运行时 + 全部依赖（勿删）
```

## 快速开始（Windows）

1. 将整个文件夹拷贝/解压到任意位置（路径可含中文、空格）；
2. 双击 `start.bat`；
3. 窗口显示 `地址: http://127.0.0.1:8000` 后约 3 秒，浏览器会自动打开该地址。

> 无需安装 Python、无需联网、无需任何配置。关闭启动窗口即停止服务。
> 页面右上角提供 **中文 / EN** 语言切换，便于对外演示。

### Linux / macOS（需自备 Python 3.10+）
```bash
bash start.sh        # 首次运行自动安装依赖（需联网）
```

### 手动启动（任意平台）
```bash
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

## 使用说明

1. 打开页面后，前端自动连接 WebSocket 并触发一次**真实引擎**映射演示；
2. 左侧台账展示 L3SM 输入（可编辑），点击 **「开始映射」** 重新执行；
3. 映射过程实时推送 trace：源字段高亮 → 规则命中脉冲 → 目标字段写入；
4. 底部指标条实时更新：**覆盖率 / 往返 diff / 溯源完整率**；
5. 后端不可用时（如仅拷贝前端），页面自动降级为内置模拟引擎。

## 【C1 新增】研究人员扩展功能

### 1. 模型 draft 上传（左栏）

三个模型层级（业务 L3SM / 网络 L3NM / 设备 OpenConfig）各有一个 draft 区：

- 输入 **draft 名称**（如 `draft-research-ext-00`）；
- 点击 **「上传 YANG draft」** 选择 `.yang` 文件上传；
- 后端自动完成：pyang 编译校验 → 保存到 `yang/drafts/<layer>/` →
  重建 `yang-library.json` → 重载 yangson DataModel；
- 上传成功后左栏显示当前激活的模块名。

### 2. 模型特征解析展示（中栏）

每个模型段顶部有 **「模型特征（YANG 解析）」** 折叠面板：

- 展示当前 draft 解析出的参数项树（容器 / 列表 / 叶子 / 类型 / 描述）；
- 上传新 draft 后自动刷新，新增参数项即时可见；
- augment 节点以 `⊕` 标记并显示挂载路径。

### 3. 映射关系定义（右栏）

**「映射关系定义（研究人员）」** 面板支持两种输入方式：

- **draft 文本**：每行一条规则，格式：
  ```
  [R7.1-01:] l3sm:vpn-services/vpn-service/vpn-id -> l3nm:vpn-services/vpn-service/vpn-id (COPY) # 说明
  l3sm:vpn-services/vpn-service/vpn-name -> - (DROP)
  ```
  支持操作：`COPY` / `DROP` / `DERIVE`；`#` 后为注释。
- **表格**：动态添加行（ID / 源字段 / 目标字段 / 操作 / 说明）。

提交后规则持久化到 `mappings/dynamic-rules.json`，**下次映射自动生效**，
trace 中以 `#R` 批次标记动态规则，可溯源。

> 路径格式：`l3sm:...` / `l3nm:...`；列表段可用 `xxx[key=value]` 定位；
> augment 引入的容器需带模块前缀（如 `ietf-l3vpn-svc-research-ext:research`）。

## 端口与配置

| 环境变量 | 默认值   | 说明               |
|----------|----------|--------------------|
| `PORT`   | `8000`   | 服务端口           |
| `HOST`   | `127.0.0.1` | 监听地址（start.sh） |

前端端口自适应：从页面 URL 自动取端口，改端口无需改前端。

## API

| 方法 | 路径      | 说明                                             |
|------|-----------|--------------------------------------------------|
| GET  | `/`       | 前端页面                                          |
| GET  | `/health` | 健康检查（含动态规则数）                           |
| POST | `/api/map`| 接收 L3SM（RFC 7951）→ L3NM + 设备 + trace + 指标 |
| WS   | `/ws/trace` | 映射过程实时推送 trace 事件                     |
| GET  | `/api/models` | 【C1】三模型层级特征树 + 当前 draft            |
| POST | `/api/draft/upload` | 【C1】上传 YANG draft（multipart）      |
| GET  | `/api/drafts` | 【C1】已上传 draft 列表                        |
| POST | `/api/mapping/define` | 【C1】定义映射关系（文本/表格）        |
| GET  | `/api/mappings` | 【C1】已定义映射规则列表                      |

## 无损指标（TC-MAP-001~003）

| 指标       | 目标   | 实测   |
|------------|--------|--------|
| 覆盖率     | 100%   | 100%   |
| 往返 diff  | =0     | =0     |
| 溯源完整率 | 100%   | 100%   |
| L3NM 校验  | valid  | valid  |

## 依赖

- **Windows 绿色版**：零依赖（内置 runtime/，Python 3.11 + 全部依赖已打包）
- **从源码运行（任意平台）**：Python ≥ 3.10，然后：

```bash
python3 -m pip install --user -r requirements.txt
```

依赖清单：fastapi / uvicorn（服务）、yangson（实例校验）、pyang（YANG 编译）、
python-multipart（draft 上传）、wsproto（WebSocket 实时 trace）

## 引擎自测（可选）

```bash
python3 -m engine.cli   # 3 个 TC 全 PASS，输出 .tmp/mapping-report.json
```

> AI生成
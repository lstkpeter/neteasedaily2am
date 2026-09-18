<div align="center">

# 🎵 NetEase2AM (网易云每日推荐 ➔ Apple Music)

**每天清晨自动将网易云音乐的“每日推荐”歌曲同步至 Apple Music 个人资料库**  
纯 Python 打造 · 全平台部署 · 智能多语言音轨匹配 · 免 Apple 开发者年费 · 开箱即用

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker Support](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-2088FF.svg?logo=github-actions&logoColor=white)](.github/workflows/daily_sync.yml)

</div>

---

## 📖 项目简介

网易云音乐的“每日推荐”算法深受许多听众的喜爱，而 Apple Music 则以无损音质（Hi-Res Lossless）、空间音频（Dolby Atmos）和纯净的原生客户端生态著称。

以往在两个平台间迁移每日推荐，往往需要使用商业转歌网站（如 TuneMyMusic / Soundiiz）手动操作，既繁琐又受限于免费额度。

**NetEase2AM** 是一个专为解决此痛点而设计的全自动化同步方案：
- **每天清晨自动唤醒**：从网易云获取当日最新 30 首推荐歌曲；
- **智能交叉匹配曲库**：自动处理日文罗马音（Hepburn）、拼音、多艺人协作（feat. / with）、官方译名及毫秒级母带时长比对；
- **自动归档或增量写入**：生成专属每日推荐歌单，醒来打开手机 Apple Music 即可直接收听！

---

## ✨ 核心特性

- 🎯 **超强多语言智能匹配算法**：
  - **罗马音全自动推导**：基于 `pykakasi` 自动将日文汉字/假名转为标准 Hepburn 罗马音，无缝匹配 Apple Music 的罗马音曲名（如 `星野源 - 恋` $\to$ `Koi`）。
  - **官方本地化译名自学习嗅探**：对于跨语种艺人（如 `いきものがかり` $\to$ `生物股长`、`ずっと真夜中でいいのに。` $\to$ `ZUTOMAYO`），引擎自动向 Apple Music 发起轻量嗅探并内存缓存官方译名，**无需人工天天维护对照表**。
  - **多艺人协作深度拆解**：智能分词识别 `feat.`、`&`、`/`、`from` 等复杂署名（如 `suis from Yorushika` $\to$ `suis`）。
  - **母带级音频时长比对（Fallback）**：针对完全意译为英文名的曲目（如《蒼の音階》被意译为《Blue Scale》），结合音频母带时长（容差 $\le 800\text{ ms}$）精准命中，严防同艺人不同歌曲串歌误判。
- 🛡️ **双 Session 隔离防限流架构**：
  - 公共曲库搜索与个人资料库接口彻底解耦，针对 Apple Music 官方 API 的单用户 429 频率限制进行专门优化，内置指数退避重试，批量同步平稳可靠。
- 🔑 **无需 Apple 开发者账号（免 $99/年）**：
  - 10 秒直接从 Apple Music 网页播放器提取合法授权 Token，零门槛零成本。
- 📱 **网易云 MUSIC_U 扫码一键获取**：
  - 内置命令行扫码助手，手机网易云扫一扫直接登录并自动保存凭证，告别繁琐的抓包与 Cookie 查找。
- 📂 **支持两种歌单管理模式**：
  - **`archive`（每日新建归档，默认推荐）**：每天自动创建独立歌单（如 `网易云日推 - 2026-09-18`），历史日推完整留存。
  - **`overwrite`（固定歌单查重追加）**：维护一个固定歌单（如 `网易云每日推荐`），每天增量查重追加新曲目。
- 🚀 **多环境一键部署**：
  - 支持 **Docker / Docker Compose**（内置 Cron 定时守护）、**Linux VPS / NAS**、以及 **GitHub Actions**（完全免服务器 0 成本托管）。
- 📊 **美观的可视化报告**：基于 `rich` 渲染实时彩色进度条与清晰直观的匹配明细报表。

---

## 📁 项目架构

```text
netease2am/
├── .github/
│   └── workflows/
│       └── daily_sync.yml        # GitHub Actions 0 成本全托管工作流
├── src/
│   ├── __init__.py
│   ├── apple_music.py            # Apple Music REST API 交互封装（双 Session 架构与 429 退避）
│   ├── config.py                 # 多源配置加载器（支持 config.json / .env / 环境变量）
│   ├── matcher.py                # 跨语种多变体智能匹配引擎（罗马音/拼音/译名嗅探/时长比对）
│   ├── netease.py                # 网易云 WeAPI 客户端（获取日推、音频别名与原声信息）
│   └── sync.py                   # 同步调度管理器与终端 Rich 渲染看板
├── .dockerignore                 # Docker 镜像打包敏感文件排除清单
├── .env.example                  # 环境变量配置模板
├── .gitignore                    # Git 提交隐私凭证防御过滤配置
├── config.example.json           # JSON 格式配置模板
├── docker-compose.yml            # Docker Compose 容器编排文件
├── Dockerfile                    # 容器化镜像构建脚本
├── entrypoint.sh                 # Docker 启动入口脚本（集成 Cron 守护与启动自检）
├── get_music_u.py                # 终端二维码扫码提取网易云 MUSIC_U 工具
├── LICENSE                       # MIT 开源许可证
├── main.py                       # CLI 命令行交互入口
├── README.md                     # 项目使用指南与文档
└── requirements.txt              # Python 依赖清单
```

---

## 🛠️ 准备工作：获取平台凭证

由于本程序基于官方合规接口工作，运行前需获取网易云音乐与 Apple Music 的凭证：

### 1. 获取网易云音乐凭证 (`MUSIC_U`)

提供两种获取方式，任选其一：

#### 方式 A：命令行扫码自动获取（最推荐）
在终端中运行项目自带的扫码工具：
```bash
python get_music_u.py
```
终端会直接打印出登录二维码，使用**网易云音乐手机 App** 扫一扫并确认登录，脚本将自动提取 `MUSIC_U` 并直接写入 `config.json`！

#### 方式 B：电脑浏览器手动提取
1. 使用电脑浏览器（Chrome / Edge / Safari）访问并登录 [网易云音乐网页版](https://music.163.com)。
2. 按 `F12`（Mac 快捷键 `Cmd + Option + I`）打开开发者工具，切换到 **Application（应用）** 标签页。
3. 在左侧选择 **Cookies** ➔ 点击 `https://music.163.com`。
4. 找到名称为 **`MUSIC_U`** 的项，复制其 **Value** 值。

---

### 2. 获取 Apple Music 凭证（10秒一键提取）

1. 在电脑浏览器中访问并登录 [Apple Music 网页版](https://music.apple.com)（确保已开通 Apple Music 会员）。
2. 登录成功后，按 `F12`（Mac 快捷键 `Cmd + Option + I`）打开开发者工具，切换到 **Console（控制台）** 标签页。
3. 复制以下一行 JavaScript 代码，粘贴到控制台并按回车执行：
   ```javascript
   copy(JSON.stringify({ developer_token: MusicKit.getInstance().developerToken, music_user_token: (MusicKit.getInstance().musicUserToken || document.cookie.match(/media-user-token=([^;]+)/)?.[1]) }, null, 2))
   ```
4. 执行后，两个 Token 已经**自动复制到了你的系统剪贴板**中！其格式如下：
   ```json
   {
     "developer_token": "eyJhbGciOi...",
     "music_user_token": "0.Aq2Q1I..."
   }
   ```

> [!TIP]
> **Token 有效期说明**：
> - `developer_token` 是 Apple Music 官方 Web 端公用分发令牌，有效期通常长达半年至数年；
> - `music_user_token` 是 Apple 为当前用户签发的持久会话凭据。正常情况下可连续稳定使用数月。若未来日志提示 `401 Unauthorized`，只需重新在浏览器控制台执行上述命令更新即可。

---

## ⚙️ 配置说明

项目支持 **`config.json` 文件** 或 **`.env` / 环境变量** 两种配置方式。

### 方式 1：使用 `config.json`（本地运行推荐）
复制模板文件：
```bash
cp config.example.json config.json
```
编辑 `config.json`：
```json
{
  "netease": {
    "music_u": "你的_MUSIC_U_凭证"
  },
  "apple_music": {
    "developer_token": "以_eyJh_开头的_developer_token",
    "music_user_token": "以_0.Aq_或类似字符开头的_music_user_token",
    "storefront": "cn"
  },
  "playlist": {
    "mode": "archive",
    "overwrite_name": "网易云每日推荐",
    "archive_prefix": "网易云日推 - ",
    "description": "由自动化任务每日自动同步网易云音乐每日推荐"
  }
}
```

### 方式 2：使用 `.env`（Docker 与容器推荐）
复制环境变量模板：
```bash
cp .env.example .env
```
根据注释填入相关参数即可。

#### 配置参数一览：

| 参数项 | 对应环境变量 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| `netease.music_u` | `NCM_MUSIC_U` | 网易云登录 Cookie 中的 MUSIC_U 值 | **必填** |
| `apple_music.developer_token` | `AM_DEVELOPER_TOKEN` | Apple Music 开发者令牌 (JWT) | **必填** |
| `apple_music.music_user_token` | `AM_MUSIC_USER_TOKEN` | Apple Music 用户私人媒体令牌 | **必填** |
| `apple_music.storefront` | `AM_STOREFRONT` | 你的 Apple ID 所在国家/地区缩写 (`cn`, `us`, `jp`, `hk`, `tw`) | `cn` |
| `playlist.mode` | `SYNC_MODE` | 歌单同步模式：`archive`（每日新建）或 `overwrite`（固定歌单追加） | `archive` |
| `playlist.overwrite_name` | `PLAYLIST_OVERWRITE_NAME` | `overwrite` 模式下的歌单名称 | `网易云每日推荐` |
| `playlist.archive_prefix` | `PLAYLIST_ARCHIVE_PREFIX` | `archive` 模式下的歌单名前缀（后接日期） | `网易云日推 - ` |
| `playlist.description` | `PLAYLIST_DESCRIPTION` | 歌单简介说明 | `由自动化任务...` |

---

## 🧪 命令行使用与连接测试

在部署定时任务之前，建议先在本地运行测试命令：

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **测试网易云音乐连接**：
   ```bash
   python main.py test-netease
   ```
   *连接正常将打印出今日网易云音乐推荐的歌曲列表。*

3. **测试 Apple Music 授权状态**：
   ```bash
   python main.py test-am
   ```
   *鉴权通过将列出你的 Apple Music 资料库现有歌单。*

4. **手动执行一次完整同步**：
   ```bash
   python main.py sync
   ```

---

## 🚢 服务器与云端部署方案

### 方案 A：Docker / Docker Compose（推荐自建 VPS / NAS）

项目内置了包含 Cron 定时守护进程的轻量化 Docker 容器。

1. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 编辑 .env 填入网易云和 Apple Music 凭据
   ```

2. **构建并启动容器**：
   ```bash
   docker compose up -d
   ```

3. **管理与日志查看**：
   - 查看容器运行状态：`docker compose ps`
   - 查看实时同步日志：`docker compose logs -f`
   - 容器会在**启动时立即执行一次同步检测**，之后默认在**每天清晨 06:30 (Asia/Shanghai)** 自动触发同步。
   - 若需修改执行时间，在 `.env` 中设置 `CRON_EXPR`（如 `CRON_EXPR=0 7 * * *` 表示每天 7:00）。

---

### 方案 B：Linux 服务器 Crontab 定时任务

若你在已有 Linux VPS 上直接运行 Python：

1. 克隆本仓库并安装依赖：
   ```bash
   git clone https://github.com/your-username/netease2am.git
   cd netease2am
   pip install -r requirements.txt
   ```
2. 配置 `config.json` 并测试运行成功。
3. 打开服务器定时任务编辑器：
   ```bash
   crontab -e
   ```
4. 添加以下定时行（每天清晨 06:30 自动执行并输出日志）：
   ```cron
   30 6 * * * cd /path/to/netease2am && /usr/bin/python3 main.py sync >> /var/log/netease2am.log 2>&1
   ```

---

### 方案 C：GitHub Actions（免服务器 0 成本全托管）

无需购买任何云服务器，借助 GitHub 免费的 Actions 定时任务每天自动跑：

1. **将代码推送到你的私有仓库**：
   > ⚠️ **强烈注意**：务必将仓库设为 **Private（私有）**，防止任何人查看你的 Action 执行记录！
2. 进入 GitHub 仓库设置：**Settings** ➔ **Secrets and variables** ➔ **Actions**。
3. 在 **Repository secrets** 中添加以下三个密钥：
   - `NCM_MUSIC_U`: 你的网易云 MUSIC_U
   - `AM_DEVELOPER_TOKEN`: 你的 Apple Music Developer Token
   - `AM_MUSIC_USER_TOKEN`: 你的 Apple Music Music-User-Token
4. （可选）在 **Repository variables** 中添加：
   - `SYNC_MODE`: `archive` 或 `overwrite`（默认 `archive`）
   - `AM_STOREFRONT`: `cn`（默认为中国大陆区）
5. 工作流定义在 [`.github/workflows/daily_sync.yml`](.github/workflows/daily_sync.yml)，每天北京时间早晨 **06:30** 会自动唤醒执行。你也可以随时在 GitHub 仓库的 **Actions** 页面手动点击 **Run workflow** 触发同步。

---

## 🧠 智能匹配引擎工作机制

为什么 NetEase2AM 能达到远高于传统转歌工具的匹配成功率？

```
网易云原曲 (标题 / 歌手 / 别名 / 时长)
   │
   ├── 1. 标题清洗：剥离 "(Live)", "(Remix)", "- EP" 等冗余干扰词
   │
   ├── 2. 罗马音与拼音推导：
   │       日文假名/汉字 ➔ Hepburn 罗马音 (恋 ➔ koi, なんもねえ ➔ nanmonee)
   │       中文 ➔ 拼音全拼
   │
   ├── 3. 跨语种官方译名动态自学习：
   │       动态向 Apple Music 嗅探官方本地化译名 (いきものがかり ➔ 生物股长, ずっと真夜中でいいのに。 ➔ ZUTOMAYO)
   │
   ├── 4. 多艺人协作分词拆解 (feat. / & / / / from)
   │
   ├── 5. 级联检索打分：
   │       优先匹配 ➔ 相似度评分 ➔ 音频时长吻合校验
   │
   └── 6. 艺人作品库母带时长比对 Fallback：
           当曲目被完全意译为不同语言（如 蒼の音階 ➔ Blue Scale）时，
           检索艺人发行库，借助毫秒级音频母带时长（误差 <= 800ms）精准锁定！
```

---

## ❓ 常见问题 (FAQ)

<details>
<summary><b>Q1: 为什么部分歌曲无法被匹配到？</b></summary>
<br>
未匹配通常由两个平台的版权差异导致，主要分为以下几种客观情况：
1. <b>流媒体未授权发行</b>：部分早期的独立音乐人同人专辑、未正式发行的小样或原声带（如 Goose house 早期自制原声带《Phrase #07 Soundtrack?》、n-buna 早期同人 Vocaloid 曲目）在全网商业流媒体均未签约上架。
2. <b>地区版权限制（锁区）</b>：若你的 Storefront 为中国大陆区（<code>cn</code>），部分仅在日本区（<code>jp</code>）或欧美区发行的歌曲在中国区曲库中不存在。程序会在终端报表中详细列出未匹配曲目。
</details>

<details>
<summary><b>Q2: 为什么 overwrite（覆盖）模式没有直接清空昨天的歌单？</b></summary>
<br>
Apple Music 官方并未对个人 Web/REST API 开放批量清空或物理删除歌单音轨的公开接口（商业转歌服务如 TuneMyMusic 同理）。
因此，本项目的 <code>overwrite</code> 模式采取<b>增量查重追加</b>机制，每天检测歌单中已有歌曲，仅向歌单中追加当天的新推荐歌曲，跳过已存在的歌曲。
<b>如果你希望每天保持只有当天纯净的 30 首歌，强烈建议使用默认的 <code>archive</code>（每日归档）模式。</b>
</details>

<details>
<summary><b>Q3: Apple Music 提示 401 Unauthorized 错误？</b></summary>
<br>
这说明你的 <code>music_user_token</code> 或 <code>developer_token</code> 已失效。只需重新打开网页版 Apple Music，按照前文步骤在控制台执行一行代码，将获取的新 Token 替换到配置文件或环境变量中即可。
</details>

---

## 🔒 免责声明与安全警告 (Disclaimer)

1. **凭证安全防范**：
   - 本项目需要使用的 `MUSIC_U` 与 `music_user_token` 包含对你相应音乐平台的个人访问授权。
   - **严禁将带有真实 Token 的 `config.json` 或 `.env` 文件提交到任何公共代码仓库（如 GitHub Public Repo）**。本项目已默认配置了 [`.gitignore`](.gitignore) 与 [`.dockerignore`](.dockerignore) 拦截关键配置文件。
   - 若使用 GitHub Actions，务必将仓库设为 **Private**，并通过 **Encrypted Secrets** 注入凭证。
2. **非官方工具说明**：
   - 本项目为个人爱好开发的开源自动化辅助脚本，与 网易公司（NetEase, Inc.） 及 苹果公司（Apple Inc.） 无任何商业隶属或关联。
   - 用户使用本工具所产生的一切网络流量与操作均代表用户自身行为，请在遵守各平台用户服务协议的前提下合理、合规使用。
3. **知识产权声明**：
   - 本项目涉及的所有音乐音轨、专辑信息、歌词与封面等版权均归属于网易云音乐、Apple Music 及其所属唱片公司或原著作权人所有。

---

## 📄 开源许可证 (License)

本项目基于 [MIT License](LICENSE) 协议开源。你可以自由地使用、修改、分发本项目的代码，但须保留原版权声明与免责声明。

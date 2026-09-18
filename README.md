# NetEase2AM

将网易云音乐“每日推荐”自动同步至 Apple Music 的轻量自动化工具。

## 功能特性

- **全自动同步**：每天定时抓取网易云每日推荐 30 首歌曲并写入 Apple Music。
- **智能跨语种匹配**：支持日语假名/汉字转罗马音（Hepburn）、拼音、多艺人协作拆解（`feat.` / `&` / `/` / `from`）及音频母带时长比对（容差 $\le 800\text{ ms}$）。
- **两种歌单模式**：
  - `archive`（推荐）：每天自动创建独立新歌单（如 `网易云日推 - 2026-09-18`）。
  - `overwrite`：向固定歌单（如 `网易云每日推荐`）增量查重追加，避免重复曲目。
- **免开发者账号**：无需付费申请 Apple 开发者证书（免 $99/年），提取 Web 授权 Token 直接调用官方 API。
- **开箱即用部署**：支持 Docker Compose 守护运行（内置定时任务）与 Linux Crontab。

## 准备工作：获取凭证

运行前需获取网易云音乐与 Apple Music 的身份凭证。

### 1. 网易云凭证 (`MUSIC_U`)

运行内置工具扫码即可自动获取并保存至 `config.json`：
```bash
pip install -r requirements.txt
python get_music_u.py
```
> 也可以在电脑浏览器登录 [music.163.com](https://music.163.com)，按 `F12` 在 **Application -> Cookies** 中复制 `MUSIC_U` 的值。

### 2. Apple Music 凭证

1. 电脑浏览器登录 [music.apple.com](https://music.apple.com)。
2. 按 `F12` 打开开发者工具，切换至 **Console（控制台）**。
3. 粘贴并回车执行以下命令：
```javascript
copy(JSON.stringify({ developer_token: MusicKit.getInstance().developerToken, music_user_token: (MusicKit.getInstance().musicUserToken || document.cookie.match(/media-user-token=([^;]+)/)?.[1]) }, null, 2))
```
执行后，`developer_token` 与 `music_user_token` 会自动复制到系统剪贴板。

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置
复制模板配置文件：
```bash
cp config.example.json config.json
```
编辑 `config.json` 填入凭证：
```json
{
  "netease": {
    "music_u": "你的 MUSIC_U"
  },
  "apple_music": {
    "developer_token": "你的 developer_token",
    "music_user_token": "你的 music_user_token",
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

### 3. 测试与运行
```bash
# 测试网易云连接
python main.py test-netease

# 测试 Apple Music 连接
python main.py test-am

# 执行一次同步
python main.py sync
```

## 服务器部署

### 方式一：Docker Compose（推荐）

1. 创建并编辑环境配置文件：
```bash
cp .env.example .env
vim .env  # 填入 NCM_MUSIC_U、AM_DEVELOPER_TOKEN、AM_MUSIC_USER_TOKEN
```
2. 启动服务：
```bash
docker compose up -d
```
> 容器启动时会自动执行一次同步，并在每天 **06:30**（Asia/Shanghai）定时运行。可通过 `.env` 中的 `CRON_EXPR` 自定义执行时间。
> 查看实时日志：`docker compose logs -f`

### 方式二：Linux Crontab

在服务器上配置系统定时任务：
```bash
crontab -e
```
添加定时执行命令（如每天 06:30 执行）：
```cron
30 6 * * * cd /path/to/netease2am && /usr/bin/python3 main.py sync >> /var/log/netease2am.log 2>&1
```

## 配置项参考

| 配置项 | 环境变量 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| `netease.music_u` | `NCM_MUSIC_U` | 网易云 Cookie 中的 `MUSIC_U` | **必填** |
| `apple_music.developer_token` | `AM_DEVELOPER_TOKEN` | Apple Music Developer Token | **必填** |
| `apple_music.music_user_token` | `AM_MUSIC_USER_TOKEN` | Apple Music User Token | **必填** |
| `apple_music.storefront` | `AM_STOREFRONT` | 商店地区代码（`cn` / `us` / `jp` / `hk` / `tw`） | `cn` |
| `playlist.mode` | `SYNC_MODE` | 同步模式：`archive`（每日新建）或 `overwrite`（固定歌单增量） | `archive` |
| `playlist.overwrite_name` | `PLAYLIST_OVERWRITE_NAME` | `overwrite` 模式下的歌单名 | `网易云每日推荐` |
| `playlist.archive_prefix` | `PLAYLIST_ARCHIVE_PREFIX` | `archive` 模式下的歌单名前缀 | `网易云日推 - ` |
| `playlist.description` | `PLAYLIST_DESCRIPTION` | 歌单描述文本 | `由自动化任务...` |

## 免责声明

- 本项目仅供个人学习与技术研究使用，请勿用于商业用途。
- 音频、封面、歌名等所有相关版权均归网易云音乐、Apple Music 及其权利人所有。
- 请妥善保管个人 Token，切勿将包含真实凭据的 `config.json` 或 `.env` 文件提交到公开代码仓库。

## License

[MIT](LICENSE)

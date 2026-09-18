import json
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class NetEaseConfig:
    music_u: str

@dataclass
class AppleMusicConfig:
    developer_token: str
    music_user_token: str
    storefront: str = "cn"

@dataclass
class PlaylistConfig:
    mode: str = "archive"  # "archive" or "overwrite"
    overwrite_name: str = "网易云每日推荐"
    archive_prefix: str = "网易云日推 - "
    description: str = "由自动化任务每日自动同步网易云音乐每日推荐"

@dataclass
class AppConfig:
    netease: NetEaseConfig
    apple_music: AppleMusicConfig
    playlist: PlaylistConfig


def load_config(config_path: str = "config.json") -> AppConfig:
    """
    优先读取 config.json，若不存在则从 .env 或环境变量中读取配置
    """
    load_dotenv()

    data = {}
    p = Path(config_path)
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] 读取 {config_path} 失败: {e}，尝试从环境变量读取")

    # 网易云配置
    music_u = (
        data.get("netease", {}).get("music_u")
        or os.getenv("NCM_MUSIC_U", "")
    ).strip()

    # Apple Music 配置
    developer_token = (
        data.get("apple_music", {}).get("developer_token")
        or os.getenv("AM_DEVELOPER_TOKEN", "")
    ).strip()
    music_user_token = (
        data.get("apple_music", {}).get("music_user_token")
        or os.getenv("AM_MUSIC_USER_TOKEN", "")
    ).strip()
    storefront = (
        data.get("apple_music", {}).get("storefront")
        or os.getenv("AM_STOREFRONT", "cn")
    ).strip()

    # 歌单配置
    p_data = data.get("playlist", {})
    mode = (p_data.get("mode") or os.getenv("SYNC_MODE", "archive")).strip().lower()
    if mode not in ("archive", "overwrite"):
        mode = "archive"

    overwrite_name = (p_data.get("overwrite_name") or os.getenv("PLAYLIST_OVERWRITE_NAME", "网易云每日推荐")).strip()
    archive_prefix = (p_data.get("archive_prefix") or os.getenv("PLAYLIST_ARCHIVE_PREFIX", "网易云日推 - ")).strip()
    description = (p_data.get("description") or os.getenv("PLAYLIST_DESCRIPTION", "由自动化任务每日自动同步网易云音乐每日推荐")).strip()

    return AppConfig(
        netease=NetEaseConfig(music_u=music_u),
        apple_music=AppleMusicConfig(
            developer_token=developer_token,
            music_user_token=music_user_token,
            storefront=storefront,
        ),
        playlist=PlaylistConfig(
            mode=mode,
            overwrite_name=overwrite_name,
            archive_prefix=archive_prefix,
            description=description,
        ),
    )

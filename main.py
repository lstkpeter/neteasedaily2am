import sys
import argparse
from rich.console import Console
from src.config import load_config
from src.sync import SyncManager
from src.netease import NetEaseClient
from src.apple_music import AppleMusicClient

console = Console()

def cmd_sync(config_path: str):
    config = load_config(config_path)
    manager = SyncManager(config)
    success = manager.run()
    sys.exit(0 if success else 1)

def cmd_test_netease(config_path: str):
    console.print("[cyan]🔍 测试网易云音乐连接...[/cyan]")
    config = load_config(config_path)
    client = NetEaseClient(music_u=config.netease.music_u)
    try:
        songs = client.get_daily_recommend_songs()
        console.print(f"[bold green]✓ 成功连接网易云接口！获取到今日推荐 {len(songs)} 首歌曲：[/bold green]")
        for i, s in enumerate(songs[:5], 1):
            console.print(f"  {i}. {s['title']} - {s['artist_str']} 《{s['album']}》")
        if len(songs) > 5:
            console.print(f"  ... 剩余 {len(songs) - 5} 首")
    except Exception as e:
        console.print(f"[bold red]❌ 测试网易云失败: {e}[/bold red]")
        sys.exit(1)

def cmd_test_am(config_path: str):
    console.print("[cyan]🔍 测试 Apple Music API 连接...[/cyan]")
    config = load_config(config_path)
    try:
        client = AppleMusicClient(
            developer_token=config.apple_music.developer_token,
            music_user_token=config.apple_music.music_user_token,
            storefront=config.apple_music.storefront,
        )
        playlists = client.get_library_playlists(limit=10)
        console.print(f"[bold green]✓ Apple Music 鉴权成功！读取到资料库歌单 {len(playlists)} 个：[/bold green]")
        for p in playlists:
            console.print(f"  - {p['name']} (ID: {p['id']})")
    except Exception as e:
        console.print(f"[bold red]❌ 测试 Apple Music 失败: {e}[/bold red]")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="网易云音乐每日推荐自动同步到 Apple Music 歌单工具"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="sync",
        choices=["sync", "test-netease", "test-am"],
        help="执行操作: sync (同步), test-netease (测试网易云), test-am (测试Apple Music)",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="配置文件路径 (默认: config.json，若不存在会自动尝试读取环境变量)",
    )

    args = parser.parse_args()

    if args.action == "sync":
        cmd_sync(args.config)
    elif args.action == "test-netease":
        cmd_test_netease(args.config)
    elif args.action == "test-am":
        cmd_test_am(args.config)

if __name__ == "__main__":
    main()

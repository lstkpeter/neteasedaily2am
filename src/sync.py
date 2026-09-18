import time
import datetime
from typing import List, Dict, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .config import AppConfig
from .netease import NetEaseClient
from .apple_music import AppleMusicClient
from .matcher import SongMatcher
from .logger import setup_logger

console = Console()

class SyncManager:
    """
    每日推荐同步管理器
    协调网易云抓取、歌曲匹配与 Apple Music 歌单写入，支持终端高亮渲染与持久化文件日志
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = setup_logger()
        self.ncm = NetEaseClient(music_u=config.netease.music_u)
        self.am = AppleMusicClient(
            developer_token=config.apple_music.developer_token,
            music_user_token=config.apple_music.music_user_token,
            storefront=config.apple_music.storefront,
        )
        self.matcher = SongMatcher(am_client=self.am)

    def run(self) -> bool:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self.logger.info(f"=== 开始网易云每日推荐 -> Apple Music 同步任务 ({today_str}) ===")
        console.print(f"\n[bold cyan]=== 开始网易云每日推荐 -> Apple Music 同步任务 ({today_str}) ===[/bold cyan]\n")

        # 1. 获取网易云每日推荐
        console.print("[yellow]正在获取网易云音乐每日推荐列表...[/yellow]")
        try:
            ncm_songs = self.ncm.get_daily_recommend_songs()
        except Exception as e:
            self.logger.error(f"获取网易云每日推荐失败: {e}", exc_info=True)
            console.print(f"[bold red]❌ 获取网易云每日推荐失败: {e}[/bold red]")
            return False

        if not ncm_songs:
            self.logger.error("未能获取到任何推荐歌曲，请检查网易云登录态。")
            console.print("[red]❌ 未能获取到任何推荐歌曲，请检查网易云登录态。[/red]")
            return False

        self.logger.info(f"成功获取网易云每日推荐 {len(ncm_songs)} 首歌曲")
        console.print(f"[green]✓ 成功获取网易云每日推荐 {len(ncm_songs)} 首歌曲[/green]\n")

        # 2. 匹配 Apple Music 曲库
        matched_results: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        unmatched_songs: List[Dict[str, Any]] = []
        am_catalog_song_ids: List[str] = []

        console.print("[yellow]正在 Apple Music 中逐首检索与匹配歌曲...[/yellow]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("匹配进度", total=len(ncm_songs))

            for song in ncm_songs:
                display_name = f"{song['title']} - {song['primary_artist']}"
                progress.update(task, description=f"匹配中: {display_name[:25]}...")
                
                try:
                    match_item = self.matcher.match(song)
                    if match_item:
                        matched_results.append((song, match_item))
                        am_catalog_song_ids.append(str(match_item["id"]))
                        self.logger.info(
                            f"[已匹配] {display_name} -> {match_item['title']} - {match_item['artist']} "
                            f"(得分: {match_item.get('match_score')}, ID: {match_item['id']})"
                        )
                    else:
                        unmatched_songs.append(song)
                        self.logger.warning(f"[未匹配] {display_name} (Apple Music 曲库无版权或未搜到)")
                except Exception as e:
                    self.logger.error(f"搜索出错: {display_name} ({e})")
                    console.print(f"[dim red]搜索出错: {display_name} ({e})[/dim red]")
                    unmatched_songs.append(song)

                time.sleep(0.1)
                progress.advance(task)

        # 3. 打印匹配统计报告
        self._print_summary_table(matched_results, unmatched_songs)

        if not am_catalog_song_ids:
            self.logger.error("匹配成功歌曲数为 0，终止歌单写入。")
            console.print("[bold red]❌ 匹配成功歌曲数为 0，终止歌单写入。[/bold red]")
            return False

        # 4. 根据模式写入 Apple Music 歌单
        mode = self.config.playlist.mode
        description = f"{self.config.playlist.description} (更新于 {today_str})"

        try:
            if mode == "archive":
                playlist_name = f"{self.config.playlist.archive_prefix}{today_str}"
                console.print(f"\n[cyan]正在创建每日归档歌单: [bold]{playlist_name}[/bold] ...[/cyan]")
                pid = self.am.create_playlist(
                    name=playlist_name,
                    description=description,
                    catalog_song_ids=am_catalog_song_ids,
                )
                self.logger.info(f"成功创建每日归档歌单: {playlist_name} (ID: {pid}, 包含歌曲: {len(am_catalog_song_ids)} 首)")
                console.print(f"[bold green]🎉 每日归档歌单创建成功！(ID: {pid})[/bold green]")

            elif mode == "overwrite":
                playlist_name = self.config.playlist.overwrite_name
                console.print(f"\n[cyan]正在同步到固定歌单: [bold]{playlist_name}[/bold] ...[/cyan]")
                existing = self.am.find_playlist_by_name(playlist_name)

                if not existing:
                    console.print(f"[yellow]歌单「{playlist_name}」不存在，正在新建...[/yellow]")
                    pid = self.am.create_playlist(
                        name=playlist_name,
                        description=description,
                        catalog_song_ids=am_catalog_song_ids,
                    )
                    self.logger.info(f"固定歌单不存在，已新建并导入 {len(am_catalog_song_ids)} 首歌曲: {playlist_name} (ID: {pid})")
                    console.print(f"[bold green]🎉 固定歌单创建成功并导入歌曲！(ID: {pid})[/bold green]")
                else:
                    pid = existing["id"]
                    console.print(f"[dim]歌单已存在 (ID: {pid})，正在检查已有歌曲并查重追加...[/dim]")
                    existing_song_ids = self.am.get_playlist_track_ids(pid)
                    to_add = [sid for sid in am_catalog_song_ids if sid not in existing_song_ids]

                    if to_add:
                        self.am.add_tracks_to_playlist(pid, to_add)
                        self.logger.info(f"成功追加 {len(to_add)} 首新歌曲到「{playlist_name}」(ID: {pid}, 跳过已存在: {len(am_catalog_song_ids) - len(to_add)} 首)")
                        console.print(f"[bold green]🎉 成功追加 {len(to_add)} 首新歌曲到「{playlist_name}」！(跳过 {len(am_catalog_song_ids) - len(to_add)} 首已存在)[/bold green]")
                    else:
                        self.logger.info(f"歌单「{playlist_name}」已包含今天所有推荐歌曲，无需重复添加。")
                        console.print(f"[bold green]✓ 歌单「{playlist_name}」已包含今天的所有推荐歌曲，无需重复添加。[/bold green]")

            self.logger.info("全部同步流程执行完毕")
            console.print("\n[bold green]✅ 全部同步流程执行完毕！打开手机或电脑 Apple Music 即可收听。[/bold green]\n")
            return True

        except Exception as e:
            self.logger.error(f"写入 Apple Music 歌单失败: {e}", exc_info=True)
            console.print(f"[bold red]❌ 写入 Apple Music 歌单失败: {e}[/bold red]")
            return False

    def _print_summary_table(
        self,
        matched: List[Tuple[Dict[str, Any], Dict[str, Any]]],
        unmatched: List[Dict[str, Any]],
    ):
        total = len(matched) + len(unmatched)
        rate = (len(matched) / total * 100) if total else 0.0
        self.logger.info(f"同步匹配统计: 共 {total} 首，已匹配 {len(matched)} 首，未匹配 {len(unmatched)} 首 (匹配率: {rate:.1f}%)")

        table = Table(title=f"同步匹配统计 (匹配率: {rate:.1f}%)")
        table.add_column("状态", style="bold", justify="center", width=8)
        table.add_column("网易云原曲 (歌名 / 歌手)", style="cyan", width=36)
        table.add_column("Apple Music 匹配结果 (歌名 / 歌手)", style="green", width=36)
        table.add_column("匹配度", justify="right", width=8)

        for ncm_s, am_s in matched[:10]:
            table.add_row(
                "[green]已匹配[/green]",
                f"{ncm_s['title']} - {ncm_s['primary_artist']}",
                f"{am_s['title']} - {am_s['artist']}",
                f"{am_s.get('match_score', 0):.2f}",
            )

        if len(matched) > 10:
            table.add_row("...", f"... 共匹配 {len(matched)} 首 ...", "...", "...")

        for s in unmatched:
            table.add_row(
                "[red]未匹配[/red]",
                f"{s['title']} - {s['primary_artist']}",
                "[dim italic]Apple Music 曲库无版权或未搜到[/dim italic]",
                "-",
            )

        console.print(table)

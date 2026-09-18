import time
import urllib.parse
from typing import List, Dict, Any, Optional, Set
import requests

class AppleMusicClient:
    """
    Apple Music REST API 客户端
    - Catalog 公共检索使用仅包含 Developer Token 的 catalog_session（避免携带用户 Token 触发 42900 频率限制）
    - Library 个人库操作使用包含 Music-User-Token 的 user_session
    """

    BASE_URL = "https://api.music.apple.com/v1"

    def __init__(self, developer_token: str, music_user_token: str, storefront: str = "cn"):
        self.developer_token = developer_token.strip()
        self.music_user_token = music_user_token.strip()
        self.storefront = storefront.strip().lower()

        if not self.developer_token:
            raise ValueError("缺少 Apple Music Developer Token")
        if not self.music_user_token:
            raise ValueError("缺少 Apple Music Music-User-Token (media-user-token)")

        browser_headers = {
            "Origin": "https://music.apple.com",
            "Referer": "https://music.apple.com/",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        # 1. 公共曲库检索 Session：严禁携带 Music-User-Token，否则极易触发 429 Too Many Requests (42900)
        self.catalog_session = requests.Session()
        self.catalog_session.headers.update({
            "Authorization": f"Bearer {self.developer_token}",
            **browser_headers,
        })

        # 2. 用户资料库 Session：用于获取/创建/编辑用户个人歌单
        self.user_session = requests.Session()
        self.user_session.headers.update({
            "Authorization": f"Bearer {self.developer_token}",
            "Music-User-Token": self.music_user_token,
            "Content-Type": "application/json",
            **browser_headers,
        })
        self.session = self.user_session

    def search_catalog_songs(self, term: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        在 Apple Music 公共曲库中搜索歌曲
        使用 catalog_session 并具备 429 退避重试能力
        """
        encoded_term = urllib.parse.quote(term)
        url = f"{self.BASE_URL}/catalog/{self.storefront}/search?term={encoded_term}&types=songs&limit={limit}"
        
        for attempt in range(3):
            try:
                resp = self.catalog_session.get(url, timeout=10)
            except Exception:
                time.sleep(1.0)
                continue

            if resp.status_code == 200:
                data = resp.json()
                songs_data = data.get("results", {}).get("songs", {}).get("data", [])
                results = []
                for item in songs_data:
                    attrs = item.get("attributes", {})
                    results.append({
                        "id": item.get("id"),
                        "title": attrs.get("name", ""),
                        "artist": attrs.get("artistName", ""),
                        "album": attrs.get("albumName", ""),
                        "duration_ms": attrs.get("durationInMillis", 0),
                        "isrc": attrs.get("isrc", "")
                    })
                return results
            elif resp.status_code == 429:
                # 触发限流，线性退避重试
                time.sleep(1.5 * (attempt + 1))
                continue
            elif resp.status_code == 401:
                raise PermissionError("Apple Music 鉴权失败 (401)，Developer Token 可能已失效。")
            else:
                return []

        return []

    def get_library_playlists(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户个人资料库中的歌单列表
        """
        url = f"{self.BASE_URL}/me/library/playlists?limit={limit}"
        resp = self.user_session.get(url)
        if resp.status_code == 401:
            raise PermissionError("Apple Music 鉴权失败 (401)，请检查 Token。")
        if resp.status_code != 200:
            return []

        data = resp.json()
        playlists = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            playlists.append({
                "id": item.get("id"),
                "name": attrs.get("name", ""),
                "can_edit": attrs.get("canEdit", False),
            })
        return playlists

    def find_playlist_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据歌单名称在用户个人库中精确查找歌单
        """
        playlists = self.get_library_playlists()
        for p in playlists:
            if p["name"] == name:
                return p
        return None

    def get_playlist_track_ids(self, playlist_id: str) -> Set[str]:
        """
        获取歌单中已存在的歌曲 Catalog ID（用于查重）
        """
        url = f"{self.BASE_URL}/me/library/playlists/{playlist_id}/tracks?limit=100"
        resp = self.user_session.get(url)
        if resp.status_code != 200:
            return set()

        data = resp.json()
        catalog_ids = set()
        for item in data.get("data", []):
            # 优先从 relationships 中提取 catalog id
            catalog_info = item.get("relationships", {}).get("catalog", {}).get("data", [])
            if catalog_info and catalog_info[0].get("id"):
                catalog_ids.add(str(catalog_info[0].get("id")))
            elif item.get("id"):
                catalog_ids.add(str(item.get("id")))
        return catalog_ids

    def create_playlist(
        self, name: str, description: str = "", catalog_song_ids: Optional[List[str]] = None
    ) -> str:
        """
        创建新的个人资料库歌单，支持同时填入初始歌曲列表
        返回新建的 playlist_id
        """
        url = f"{self.BASE_URL}/me/library/playlists"
        payload: Dict[str, Any] = {
            "attributes": {
                "name": name,
                "description": description,
            }
        }

        if catalog_song_ids:
            payload["relationships"] = {
                "tracks": {
                    "data": [{"id": sid, "type": "songs"} for sid in catalog_song_ids]
                }
            }

        resp = self.user_session.post(url, json=payload)
        if resp.status_code not in (201, 200):
            raise RuntimeError(f"创建 Apple Music 歌单失败 [{resp.status_code}]: {resp.text}")

        res_data = resp.json()
        items = res_data.get("data", [])
        if not items:
            raise RuntimeError("创建歌单成功但未返回有效歌单数据")
        return items[0]["id"]

    def add_tracks_to_playlist(self, playlist_id: str, catalog_song_ids: List[str]) -> bool:
        """
        向现有歌单追加歌曲
        """
        if not catalog_song_ids:
            return True

        url = f"{self.BASE_URL}/me/library/playlists/{playlist_id}/tracks"
        payload = {
            "data": [{"id": sid, "type": "songs"} for sid in catalog_song_ids]
        }

        resp = self.user_session.post(url, json=payload)
        if resp.status_code in (204, 201, 200):
            return True

        raise RuntimeError(f"向歌单追加歌曲失败 [{resp.status_code}]: {resp.text}")

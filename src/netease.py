from typing import List, Dict, Any
from netease_encode_api import EncodeSession

class NetEaseClient:
    """
    网易云音乐 API 客户端
    使用 Weapi 接口获取用户的每日推荐歌曲
    """

    def __init__(self, music_u: str = ""):
        self.session = EncodeSession()
        if music_u:
            self.session.cookies.set("MUSIC_U", music_u, domain=".music.163.com")
            self.session.cookies.set("os", "pc", domain=".music.163.com")
            self.session.cookies.set("appver", "2.9.7", domain=".music.163.com")

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://music.163.com/",
            "Origin": "https://music.163.com"
        })

    def get_daily_recommend_songs(self) -> List[Dict[str, Any]]:
        """
        获取每日推荐歌曲列表
        返回包含歌曲名、艺术家列表、专辑名的字典列表
        """
        url = "https://music.163.com/weapi/v3/discovery/recommend/songs"
        try:
            resp = self.session.encoded_post(url, {})
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"请求网易云每日推荐接口网络异常: {e}")

        code = data.get("code")
        if code != 200:
            msg = data.get("message") or str(code)
            raise RuntimeError(
                f"获取网易云每日推荐失败 (code: {code}, msg: {msg})。"
                "请检查 MUSIC_U Cookie 是否配置正确或已过期。"
            )

        daily_songs = data.get("data", {}).get("dailySongs", [])
        if not daily_songs:
            # 有时可能在推荐列表的另外字段中
            daily_songs = data.get("recommend", [])

        result = []
        for s in daily_songs:
            song_id = s.get("id")
            name = (s.get("name") or "").strip()
            artists = [a.get("name", "").strip() for a in s.get("ar", []) if a.get("name")]
            album_name = s.get("al", {}).get("name", "").strip() if s.get("al") else ""

            if not name:
                continue

            aliases = [a.strip() for a in s.get("alia", []) if isinstance(a, str) and a.strip()]
            translations = [t.strip() for t in s.get("tns", []) if isinstance(t, str) and t.strip()]

            artist_aliases = []
            for a in s.get("ar", []):
                for item in a.get("alias", []) + a.get("tns", []):
                    if isinstance(item, str) and item.strip() and item.strip() not in artist_aliases:
                        artist_aliases.append(item.strip())

            result.append({
                "id": song_id,
                "title": name,
                "aliases": aliases,
                "translations": translations,
                "artists": artists,
                "primary_artist": artists[0] if artists else "",
                "artist_str": " / ".join(artists),
                "artist_aliases": artist_aliases,
                "album": album_name,
                "duration_ms": s.get("dt", 0),
            })

        return result

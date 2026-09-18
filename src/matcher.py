import re
import difflib
from typing import Dict, Any, Optional, List, Set
import pykakasi
from pypinyin import lazy_pinyin
from .apple_music import AppleMusicClient

# 常见高频跨语言艺人种子词典（可选缓存预热，用于极速减少 API 请求数）
# 注意：引擎不依赖此硬编码词典！对于字典外的任意未知艺人，引擎会自动通过：
# 1) pykakasi / pypinyin 罗马音与拼音自动变体生成
# 2) 动态向 Apple Music 嗅探官方本地化别名 (self._fetch_am_localized_artist) 并内存自学习缓存
# 3) 音频母带毫秒级时长比对（<= 800ms 容差）
# 从而实现完全动态、自适应的每日未知新歌匹配。
KNOWN_ARTIST_MAP: Dict[str, List[str]] = {
    "星野源": ["Gen Hoshino"],
    "ヨルシカ": ["Yorushika"],
    "サカナクション": ["鱼韵", "Sakanaction"],
    "いきものがかり": ["生物股长", "Ikimonogakari"],
    "あいみょん": ["爱缪", "Aimyon"],
    "ずっと真夜中でいいのに。": ["ZUTOMAYO"],
    "ゲシュタルト乙女": ["Gestalt Girl"],
    "ネクライトーキー": ["Necry Talkie"],
    "椎名林檎": ["Sheena Ringo"],
    "宇多田ヒカル": ["宇多田光", "Hikaru Utada"],
    "米津玄師": ["米津玄师", "Kenshi Yonezu"],
    "水曜日のカンパネラ": ["星期三的康帕内拉", "Wednesday Campanella"],
    "神様、僕は気づいてしまった": ["神阿、我已经察觉到了", "Kami-sama, I have noticed"],
    "女王蜂": ["QUEEN BEE"],
    "東京事変": ["东京事变", "Tokyo Jihen"],
    "緑黄色社会": ["绿黄色社会", "Ryokuoushoku Shakai"],
    "結束バンド": ["团结Band", "Kessoku Band"],
    "平井堅": ["平井坚", "Ken Hirai"],
    "大原ゆい子": ["大原悠衣子", "Yuiko Ohara"],
    "ナナツカゼ": ["nanatsukaze"],
    "suis": ["suis from Yorushika"],
}

# 自动建立双向映射
for _k, _vals in list(KNOWN_ARTIST_MAP.items()):
    for _v in _vals:
        if _v not in KNOWN_ARTIST_MAP:
            KNOWN_ARTIST_MAP[_v] = [_k]
        elif _k not in KNOWN_ARTIST_MAP[_v]:
            KNOWN_ARTIST_MAP[_v].append(_k)


class SongMatcher:
    """
    歌曲跨平台多语言智能匹配引擎
    核心机制：
    1. 假名/汉字转罗马音（Hepburn）和拼音多变体生成（全自动，无需维护字典）
    2. 细分多艺人协作（feat.、&、/、from 等）拆解与独立匹配
    3. Apple Music 官方本地化译名全自动动态嗅探与自学习缓存
    4. 艺人作品库 Fallback 机制：当歌名被意译为完全无关英文名时（如 蒼の音階 -> Blue Scale），
       检索该艺人作品并结合毫秒级音频母带时长（<= 800ms 误差）精准识别
    5. 彻底杜绝同艺人不同歌曲之间的误串（如 Goose house 的《You》绝不误判为《ごはんを食べよう》）
    """

    def __init__(self, am_client: AppleMusicClient, threshold: float = 0.58):
        self.am_client = am_client
        self.threshold = threshold
        self.kakasi = pykakasi.kakasi()
        self._artist_localized_cache: Dict[str, List[str]] = {}

    @staticmethod
    def clean_text(text: str) -> str:
        """
        去除括号内的版本干扰词及后缀，如 (Live), (Remix), (feat. xxx), - Single, - EP
        """
        if not text:
            return ""
        t = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
        t = re.sub(r"\s+-\s+(Single|EP|Album|Soundtrack\?|Live)$", "", t, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", t).strip()

    def get_romaji(self, text: str) -> str:
        """
        日文假名/汉字转罗马音 (Hepburn)
        """
        if not text:
            return ""
        try:
            res = self.kakasi.convert(text)
            return " ".join([item["hepburn"].lower() for item in res if item.get("hepburn")]).strip()
        except Exception:
            return ""

    def get_pinyin(self, text: str) -> str:
        """
        中文转拼音
        """
        if not text:
            return ""
        try:
            return " ".join(lazy_pinyin(text)).strip().lower()
        except Exception:
            return ""

    def get_title_variants(self, title: str, extras: Optional[List[str]] = None) -> List[str]:
        """
        生成歌曲名称的多语言变体集合：原名、清洗名、罗马音、拼音、网易云翻译/别名
        """
        if not title:
            return []

        clean = self.clean_text(title)
        variants: Set[str] = {title.lower().strip(), clean.lower().strip()}

        # 罗马音变体 (如 "恋" -> "koi", "なんもねえ" -> "nanmonee", "春めく" -> "harumeku")
        romaji = self.get_romaji(title)
        if romaji:
            variants.add(romaji)
            variants.add(romaji.replace(" ", ""))

        # 拼音变体
        pinyin = self.get_pinyin(title)
        if pinyin:
            variants.add(pinyin)
            variants.add(pinyin.replace(" ", ""))

        # 网易云返回的翻译/别名
        for item in extras or []:
            if item and isinstance(item, str):
                item_clean = self.clean_text(item).lower().strip()
                if item_clean:
                    variants.add(item.lower().strip())
                    variants.add(item_clean)
                    r = self.get_romaji(item_clean)
                    if r:
                        variants.add(r)
                        variants.add(r.replace(" ", ""))

        return [v for v in variants if v]

    def get_artist_variants(self, artist: str, extra_aliases: Optional[List[str]] = None) -> List[str]:
        """
        生成艺人名称的多语言变体集合：原名、常用对照表、罗马音（正序/倒序）、拼音
        """
        if not artist:
            return []

        clean_art = self.clean_text(artist)
        variants: Set[str] = {artist.lower().strip(), clean_art.lower().strip()}

        # 1. 常用艺人翻译库对照
        for alias in KNOWN_ARTIST_MAP.get(artist, []) + KNOWN_ARTIST_MAP.get(clean_art, []):
            variants.add(alias.lower().strip())

        for extra in extra_aliases or []:
            if extra and isinstance(extra, str):
                variants.add(extra.lower().strip())

        # 2. 罗马音 (支持 姓 名 和 名 姓 顺序)
        try:
            res = self.kakasi.convert(clean_art)
            hepburn_list = [item["hepburn"].lower() for item in res if item.get("hepburn")]
            if hepburn_list:
                variants.add(" ".join(hepburn_list))
                variants.add("".join(hepburn_list))
                if len(hepburn_list) == 2:
                    variants.add(f"{hepburn_list[1]} {hepburn_list[0]}")
                    variants.add(f"{hepburn_list[1]}{hepburn_list[0]}")
        except Exception:
            pass

        # 3. 拼音
        pinyin = self.get_pinyin(clean_art)
        if pinyin:
            variants.add(pinyin)
            variants.add(pinyin.replace(" ", ""))

        # 4. 动态探测 Apple Music 官方本地化译名（完全摆脱对硬编码对照表的依赖）
        if not artist.isascii():
            for loc in self._fetch_am_localized_artist(clean_art):
                variants.add(loc.lower().strip())

        return [v for v in variants if v]

    def _fetch_am_localized_artist(self, artist: str) -> List[str]:
        """
        向 Apple Music 发起轻量检索，动态探测该艺人在当前 Storefront 的官方本地化译名（如 いきものがかり -> 生物股长）
        自带内存缓存，相同艺人仅检索一次
        """
        if not artist or not self.am_client:
            return []
        clean_art = self.clean_text(artist)
        if clean_art in self._artist_localized_cache:
            return self._artist_localized_cache[clean_art]

        found = []
        try:
            res = self.am_client.search_catalog_songs(clean_art, limit=3)
            for r in res:
                cand_art = r.get("artist", "").strip()
                if cand_art and cand_art not in found:
                    found.append(cand_art)
                    # 拆解复合艺人名
                    parts = re.split(r"[,&/、+;]|\bfeat\b\.?|\bfeaturing\b|\bwith\b|\bfrom\b", cand_art, flags=re.IGNORECASE)
                    for p in parts:
                        p_clean = self.clean_text(p).strip()
                        if p_clean and p_clean not in found:
                            found.append(p_clean)
        except Exception:
            pass

        self._artist_localized_cache[clean_art] = found
        return found

    def _match_artist_score(self, target_art_vars: List[str], cand_artist_str: str) -> float:
        """
        支持多艺人拆分（如 ナナツカゼ, PIKASONIC & nakotanmaru 或 suis from Yorushika）
        """
        if not cand_artist_str or not target_art_vars:
            return 0.0

        cand_clean = self.clean_text(cand_artist_str).lower()
        cand_parts = re.split(r"[,&/、+;]|\bfeat\b\.?|\bfeaturing\b|\bwith\b|\bfrom\b", cand_artist_str, flags=re.IGNORECASE)
        cand_components = [self.clean_text(p).lower() for p in cand_parts if p.strip()]
        cand_tokens = set(re.findall(r"[\w\u4e00-\u9fff\u3040-\u30ff]+", cand_artist_str.lower()))

        best_score = 0.0
        for tv in target_art_vars:
            tv_lower = tv.lower().strip()
            # 完整匹配或词级独立匹配
            if tv_lower == cand_clean or tv_lower in cand_tokens:
                return 1.0
            for comp in cand_components:
                if tv_lower == comp or (len(tv_lower) >= 3 and tv_lower in comp):
                    return 1.0
                sim = difflib.SequenceMatcher(None, tv_lower, comp).ratio()
                if sim > best_score:
                    best_score = sim

        return best_score

    def _match_title_score(self, target_title_vars: List[str], cand_title_str: str) -> float:
        """
        对比候选歌名与所有可能标题变体的最高吻合度
        """
        if not cand_title_str or not target_title_vars:
            return 0.0

        c_raw = cand_title_str.lower().strip()
        c_clean = self.clean_text(cand_title_str).lower().strip()

        best = 0.0
        for v in target_title_vars:
            if v == c_raw or v == c_clean:
                return 1.0
            # 忽略空格匹配 (如 "haru meku" vs "harumeku")
            if v.replace(" ", "") == c_clean.replace(" ", ""):
                return 0.98

            # 子串包含对比 (如 "Koi - EP" 包含 "Koi")
            if (v in c_clean or c_clean in v) and (len(v) >= 3 and len(c_clean) >= 3):
                len_ratio = min(len(v), len(c_clean)) / max(len(v), len(c_clean))
                if len_ratio >= 0.75:
                    return 0.88
                else:
                    sub_score = len_ratio * 0.50
                    if sub_score > best:
                        best = sub_score
                    continue

            sim = difflib.SequenceMatcher(None, v, c_clean).ratio()
            if sim > best:
                best = sim

        return best

    def _score_candidate(
        self,
        cand: Dict[str, Any],
        title_variants: List[str],
        artist_variants: List[str],
        target_dur_ms: int,
    ) -> float:
        cand_title = cand.get("title", "")
        cand_artist = cand.get("artist", "")
        cand_dur_ms = cand.get("duration_ms", 0)

        a_sim = self._match_artist_score(artist_variants, cand_artist)
        # 核心防误判 1：如果艺人完全不搭边 (a_sim < 0.40)，坚决不匹配！
        if a_sim < 0.40:
            return 0.0

        t_sim = self._match_title_score(title_variants, cand_title)
        dur_diff = abs(cand_dur_ms - target_dur_ms) if (target_dur_ms and cand_dur_ms) else 999999

        # 核心防误判 2：
        # 歌名完全不吻合 (t_sim < 0.45) 的情形（如 蒼の音階 vs Blue Scale，或 ごはんを食べよう vs You）
        # 只有在【艺人高度吻合 (>= 0.80) 且音频时长误差 <= 800ms (同母带/0.8秒内)】时才允许作为意译英文曲名匹配！
        if t_sim < 0.45:
            if a_sim >= 0.80 and dur_diff <= 800:
                return 0.95
            else:
                # 严厉杜绝同艺人的不同歌曲！(如 Goose house 的 You 与 ごはんを食べよう 时长差 1.8 秒，立即排除)
                return 0.0

        # 核心防误判 3：
        # 如果音轨时长相差超过 4 秒 (dur_diff > 4000)，除非歌名高度一致 (t_sim >= 0.85)，否则坚决拒绝！
        # 杜绝同一艺人由于字母重叠（如 iranai 与 Wasurerarenaino 相差 13.6 秒）发生串歌误判
        if dur_diff > 4000 and t_sim < 0.85:
            return 0.0

        # 情形 A：歌名高度吻合 (>= 0.80)（原名或罗马音）
        if t_sim >= 0.80:
            return max(0.90, 0.5 * t_sim + 0.5 * a_sim)

        # 情形 B：歌名中度吻合 (0.45 <= t_sim < 0.80)
        # 要求艺人匹配，且时长误差必须在合理范围内 (<= 2500ms)
        if a_sim >= 0.60 and dur_diff <= 2500:
            return 0.85

        return 0.55 * t_sim + 0.45 * a_sim

    def match(self, target_song: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        传入网易云歌曲信息，智能检索并打分返回最佳匹配的 Apple Music 歌曲
        """
        title = target_song.get("title", "").strip()
        primary_artist = target_song.get("primary_artist", "").strip()
        target_dur_ms = target_song.get("duration_ms", 0)

        # 提取网易云附带的别名与翻译
        extras = target_song.get("aliases", []) + target_song.get("translations", [])
        title_variants = self.get_title_variants(title, extras)

        artist_extras = target_song.get("artist_aliases", [])
        artist_variants: List[str] = []
        for art in target_song.get("artists", [primary_artist]):
            artist_variants.extend(self.get_artist_variants(art, artist_extras))

        # 构建优先级搜索检索词
        queries: List[str] = [
            f"{primary_artist} {title}",
            f"{title} {primary_artist}",
        ]

        # 罗马音检索词
        romaji_titles = [v for v in title_variants if v != title.lower() and re.match(r"^[a-z0-9\s]+$", v)]
        if romaji_titles:
            queries.append(f"{primary_artist} {romaji_titles[0]}")
            if artist_variants:
                queries.append(f"{artist_variants[0]} {romaji_titles[0]}")

        # 动态探测到的艺人本地化名称作为检索词 (如 "鱼韵 いらない", "生物股长 さよならララ")
        for art_var in artist_variants:
            if art_var != primary_artist.lower():
                queries.append(f"{art_var} {title}")
                if romaji_titles:
                    queries.append(f"{art_var} {romaji_titles[0]}")

        seen_ids = set()
        candidates: List[Dict[str, Any]] = []

        for q in queries:
            results = self.am_client.search_catalog_songs(q, limit=5)
            has_high_score = False
            for cand in results:
                cid = cand.get("id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates.append(cand)
                    # 提前打分探测：如果已经搜到了高确信度结果 (>= 0.90)，立即停止后续多余搜索节省请求
                    score = self._score_candidate(cand, title_variants, artist_variants, target_dur_ms)
                    if score >= 0.90:
                        has_high_score = True
            if has_high_score or len(candidates) >= 12:
                break

        # Fallback 机制：
        # 如果以上检索均未命中属于该艺人的任何歌曲（如 涼海ネモ 的《蒼の音階》被 Apple Music 翻译成了《Blue Scale》且普通搜索不出）
        # 则直接获取该艺人的发行作品库进行母带级（<= 800ms）时长智能比对
        has_matching_artist = any(self._match_artist_score(artist_variants, c.get("artist", "")) >= 0.60 for c in candidates)
        if not has_matching_artist and primary_artist:
            artist_catalog_results = self.am_client.search_catalog_songs(primary_artist, limit=25)
            for cand in artist_catalog_results:
                cid = cand.get("id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates.append(cand)

        if not candidates:
            return None

        # 打分排序
        scored = []
        for cand in candidates:
            score = self._score_candidate(cand, title_variants, artist_variants, target_dur_ms)
            if score > 0:
                scored.append((score, cand))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_cand = scored[0]

        if best_score >= self.threshold:
            best_cand["match_score"] = round(best_score, 2)
            return best_cand

        return None

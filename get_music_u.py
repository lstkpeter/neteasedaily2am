import time
import json
import re
from pathlib import Path
import pyqrcode
from rich.console import Console
from netease_encode_api import EncodeSession

console = Console()

def main():
    console.print("\n[bold cyan]=== 网易云音乐 MUSIC_U 扫码自动获取助手 ===[/bold cyan]\n")
    console.print("[dim]正在向网易云服务器申请登录二维码...[/dim]")

    session = EncodeSession()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://music.163.com/",
        "Origin": "https://music.163.com",
    })

    try:
        # 1. 申请 unikey
        resp = session.encoded_post("https://music.163.com/weapi/login/qrcode/unikey", {"type": 1})
        unikey = resp.json().get("unikey")
        if not unikey:
            console.print("[red]❌ 获取二维码 Key 失败[/red]")
            return
    except Exception as e:
        console.print(f"[red]❌ 请求接口异常: {e}[/red]")
        return

    qr_url = f"https://music.163.com/login?codekey={unikey}"
    qr = pyqrcode.create(qr_url)

    console.print("[yellow]请使用【网易云音乐手机 App】扫一扫下方二维码登录：[/yellow]\n")
    text = qr.text()
    for line in text.strip().split("\n"):
        print("".join(["  " if c == "0" else "██" for c in line]))
    print()

    # 2. 轮询扫码状态
    console.print("[cyan]正在等待手机端扫码并确认...[/cyan]")
    music_u = None

    while True:
        time.sleep(2)
        try:
            chk_resp = session.encoded_post(
                "https://music.163.com/weapi/login/qrcode/client/login",
                {"key": unikey, "type": 1},
            )
            data = chk_resp.json()
            code = data.get("code")

            if code == 800:
                console.print("[red]❌ 二维码已过期，请重新运行脚本。[/red]")
                break
            elif code == 801:
                # 等待扫码
                continue
            elif code == 802:
                console.print("[blue]📱 已扫描，请在手机上点击【授权登录】...[/blue]")
            elif code == 803:
                console.print("[bold green]🎉 授权登录成功！[/bold green]")
                # 尝试从 cookie 字段提取
                cookie_str = data.get("cookie", "")
                m = re.search(r"MUSIC_U=([^;]+)", cookie_str)
                if m:
                    music_u = m.group(1)
                else:
                    # 尝试从 session cookies 中提取
                    music_u = session.cookies.get("MUSIC_U") or chk_resp.cookies.get("MUSIC_U")

                break
        except Exception as e:
            console.print(f"[dim red]检测状态异常: {e}[/dim red]")
            time.sleep(1)

    if music_u:
        console.print(f"\n[bold green]✓ 成功捕获到 MUSIC_U:[/bold green]\n[yellow]{music_u}[/yellow]\n")

        # 尝试自动写入 config.json
        config_path = Path("config.json")
        if not config_path.exists() and Path("config.example.json").exists():
            with open("config.example.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
        elif config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {"netease": {}, "apple_music": {}, "playlist": {}}

        if "netease" not in cfg:
            cfg["netease"] = {}
        cfg["netease"]["music_u"] = music_u

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        console.print(f"[bold green]✓ 已自动将 MUSIC_U 保存到 {config_path.resolve()}[/bold green]")
    else:
        console.print("[red]未能成功提取到 MUSIC_U，请尝试手动从浏览器获取。[/red]")

if __name__ == "__main__":
    main()

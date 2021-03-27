from .download_radclass import *

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()


def download_rad():
    print("#####Radar Downloader#####")
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    try:
        # クラス
        t = DownloadRadar()
        # ダウンロード
        t.download_jp_radar()
    except Exception as e:
        exit_program(e, sys.exc_info())
    exit_program("完了しました")

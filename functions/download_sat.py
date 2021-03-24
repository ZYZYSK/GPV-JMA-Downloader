from .download_satclass import *

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()


def download_sat():
    print("#####Satellite Downloader#####")
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    # クラス
    t = DownloadSatellite()
    # ダウンロード
    t.download_jp_infrared()
    t.download_jp_visible()
    t.download_jp_watervapor()
    t.download_jp_truecolor()
    t.download_jp_cloudheight()
    exit_program("完了しました")

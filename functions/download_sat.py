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
    t.download_j_infrared()
    t.download_j_visible()
    t.download_j_watervapor()
    t.download_j_truecolor()
    t.download_j_cloudheight()

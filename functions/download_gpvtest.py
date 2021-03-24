from .download_gpvclass import *

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()


def download_gpvtest():
    print("#####GPV Downloader#####")
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    # 設定ファイルの読み込み
    with open("settings_gpv.json") as fp:
        settings = json.load(fp)
    # ディレクトリが存在しなければ作成
    try:
        for dirs in settings["path"].values():
            os.makedirs(dirs, exist_ok=True)
    except FileNotFoundError:
        exit_program(f'{settings["path"]}は存在しないパスです.')
    # ダウンロード時刻は一日前
    time_this = datetime.date.today() - datetime.timedelta(days=1)
    # ダウンロードと天気図作成
    try:
        t = DownloadGPV(time_this, settings["fig_x"], settings["fig_y"], settings["path"]["tmp"])
        t.download_grib2()
        t.test()
    except Exception as e:
        exit_program(e, sys.exc_info())
    # 完了
    exit_program("完了しました")

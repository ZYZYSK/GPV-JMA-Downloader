from .download_msmclass import *
from .download_gsm import update_settings
if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()


def download_msm():
    print("#####MSM Downloader#####")
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    # 設定ファイルの読み込み
    with open("settings_msm.json") as fp:
        settings = json.load(fp)
    # ディレクトリが存在しなければ作成
    try:
        for dirs in settings["path"].values():
            os.makedirs(dirs, exist_ok=True)
    except FileNotFoundError:
        exit_program(f'{settings["path"]}は存在しないパスです.')
    # ダウンロード開始時刻の設定
    try:
        time_start = datetime.datetime(settings["time_start"]["year"], settings["time_start"]["month"], settings["time_start"]["day"], 0, 0)
    except Exception as e:
        exit_program(e, sys.exc_info())
    print(f'ダウンロード開始日時(UTC): {time_start}')
    # ダウンロード終了時刻は一日前
    time_end = datetime.date.today() - datetime.timedelta(days=1)
    # ダウンロードと天気図作成
    while time_start.date() < time_end:
        try:
            t = DownloadMSM(time_start, settings["fig_x"], settings["fig_y"], settings["path"]["tmp"])
            t.download_grib2()
            t.jp_surf_ppc(settings["path"]["jp_surf_ppc"])
        except Exception as e:
            exit_program(e, sys.exc_info())
        time_start += datetime.timedelta(hours=3)
    # grib2ファイルの削除
    if(settings["delete_tmp"]):
        shutil.rmtree(settings["path"]["tmp"])
    # 設定の更新
    update_settings(settings, time_start, "settings_msm.json")
    # 完了
    exit_program("完了しました")

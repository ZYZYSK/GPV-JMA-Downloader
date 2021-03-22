from .download_gpvclass import *

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()


def download_gpv():
    print("#####GPV Downloader#####")
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    # 設定ファイルの読み込み
    settings = None
    with open("settings_gpv.json") as fp:
        settings = json.load(fp)
    # ファイルの保存場所に移動
    try:
        # ディレクトリが存在しなければ作成
        os.makedirs(settings["path"], exist_ok=True)
        os.chdir(settings["path"])
    except FileNotFoundError:
        exit_program(f'{settings["path"]}は存在しないパスです.')
    # ディレクトリが存在しなければ作成
    dir_list = ['tmp', 'j300hw', 'j500ht', 'j500hv', 'j500t700td', 'j850ht', 'j850tw700vv', 'j850eptw']
    for dirs in dir_list:
        os.makedirs(dirs, exist_ok=True)
    # ダウンロード開始時刻の設定
    try:
        time_start = datetime.datetime(settings["time_start"]["year"], settings["time_start"]["month"], settings["time_start"]["day"], 0, 0) - datetime.timedelta(hours=6 * (DownloadGPV.time_diff // 6))
        time_start_jp = time_start + datetime.timedelta(hours=DownloadGPV.time_diff)
    except Exception as e:
        exit_program(e, sys.exc_info())
    print(f'ダウンロード開始日時: {time_start_jp}')
    # ダウンロード終了時刻は一日前
    time_end = datetime.date.today() - datetime.timedelta(days=1)
    # ダウンロードと天気図作成
    while time_start_jp.date() < time_end:
        try:
            t = DownloadGPV(time_start, settings["fig_x"], settings["fig_y"])
            t.download_grib2()
            t.make_map()
        except Exception as e:
            exit_program(e, sys.exc_info())
        time_start += datetime.timedelta(hours=6)
    # grib2ファイルの削除
    if(settings["delete_tmp"]):
        shutil.rmtree("tmp")
    # 設定の更新
    settings["time_start"]["year"] = time_start.year
    settings["time_start"]["month"] = time_start.month
    settings["time_start"]["day"] = time_start.day
    os.chdir(os.path.join(Path(__file__).resolve().parent.parent))
    with open("settings_gpv.json", "w") as fp:
        json.dump(settings, fp)
    print("#####完了#####")

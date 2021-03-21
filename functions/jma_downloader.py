import os
import shutil
import sys
import time as tm
import datetime
import requests
from concurrent import futures
import logging
import signal


from . import exit_program, handler_sigint, file_is_on_server

# ログ出力の無効化
# logging.disable(logging.CRITICAL)
# ログ出力設定
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')


def jma_downloader():
    # SIGINTシグナルを受け取る
    signal.signal(signal.SIGINT, handler_sigint)
    print('___JMA Downloader___')
    # ファイルの保存場所とダウンロード開始日時の情報を取得
    JmaDownloader.get_settings()
    # ファイルの保存場所に移動
    JmaDownloader.move_path()
    # ジョブリスト
    job_list = []

    # debug
    logging.warning("クラス変数準備完了\nクラス初期化")

    # クラスの指定　
    infrared = JmaDownloader('infrared', 'https://www.jma.go.jp/jp/gms/imgs_c/0/infrared/1/', 10)
    infrared_earth = JmaDownloader('infrared_earth', 'https://www.jma.go.jp/jp/gms/imgs_c/6/infrared/1/', 10)
    radar = JmaDownloader('radar', 'https://www.jma.go.jp/jp/radnowc/imgs/radar/000/', 5)
    visible = JmaDownloader('visible', 'https://www.jma.go.jp/jp/gms/imgs_c/0/visible/1/', 10)
    visible_earth = JmaDownloader('visible_earth', 'https://www.jma.go.jp/jp/gms/imgs_c/6/visible/1/', 10)
    watervapor = JmaDownloader('watervapor', 'https://www.jma.go.jp/jp/gms/imgs_c/0/watervapor/1/', 10)
    watervapor_earth = JmaDownloader('watervapor_earth', 'https://www.jma.go.jp/jp/gms/imgs_c/6/watervapor/1/', 10)
    weather_map = JmaDownloaderWeatherMap('weather_map', 'https://www.jma.go.jp/jp/g3/images/jp_c/', 180)
    # debug
    logging.warning("クラスの指定が完了")

    # クラスリスト
    jma_list = [infrared, infrared_earth, radar, visible,
                visible_earth, watervapor, watervapor_earth, weather_map]
    # debug
    logging.warning("ダウンロード準備完了")

    # ダウンロード
    # with futures.ProcessPoolExecutor(max_workers=len(jma_list)) as executor:
    with futures.ProcessPoolExecutor(max_workers=2) as executor:
        for i in jma_list:
            job_list.append(executor.submit(i.download_map))
        _ = futures.as_completed(fs=job_list)
    logging.warning("ダウンロード終了")


class JmaDownloader:
    # 設定ファイルの場所
    settings_file_path = os.path.join(os.path.dirname(__file__), 'jma_settings.txt')
    # 何日前から
    days_duration = 6
    # 保存場所
    path = None

    @classmethod
    def get_settings(cls):  # 設定ファイルを読み込み，"データの保存場所"を取得
        # 設定ファイルを開く
        try:
            with open(cls.settings_file_path, mode='r') as f:
                cls.path = f.readline().strip('\n')

        # 設定ファイルが見つからなかった場合
        except FileNotFoundError:
            # 設定ファイルを新規作成
            with open(cls.settings_file_path, mode='w') as f:
                pass

        # 設定ファイルに何も書かれていなかった場合
        if cls.path is None:
            exit_program("\"データの保存場所\"が指定されていません．{0} を正しく設定してください．".format(cls.settings_file_path))

        print('保存先： {0}'.format(cls.path))

    @classmethod
    def move_path(cls):
        # "データの保存場所"に移動
        try:
            # "データの保存場所"が存在しない場合は，ディレクトリを作成
            os.makedirs(cls.path, exist_ok=True)
            # 移動
            os.chdir(cls.path)

        # "データの保存場所"が正しくない場合
        except FileNotFoundError:
            exit_program("\"データの保存場所\"が正しくありません．{0} を正しく設定してください．".format(cls.settings_file_path))

    def __init__(self, map_name, map_url, interval):  # 初期化
        logging.warning("{0} 初期化開始 {1}".format(map_name, self))
        # 画像の種類
        self.map_name = map_name
        # URL
        self.map_url = map_url
        # 日時の間隔(分)
        self.interval = interval
        # 開始日時
        self.time_now = datetime.datetime.now() - datetime.timedelta(days=self.days_duration)
        # 開始日時をintervalの倍数に変換
        if self.interval <= 60:
            self.time_now = datetime.datetime(self.time_now.year, self.time_now.month, self.time_now.day, self.time_now.hour, self.time_now.minute // self.interval * self.interval)
        elif self.interval > 60 and self.interval % 60 == 0:
            self.time_now = datetime.datetime(self.time_now.year, self.time_now.month, self.time_now.day, self.time_now.hour // (self.interval // 60) * (self.interval // 60), 00)
        # 終了日時
        self.time_end = datetime.datetime.now() - datetime.timedelta(minutes=self.interval)
        # フォルダの作成
        os.makedirs(self.map_name, exist_ok=True)
        logging.warning("初期化終了")

    def download_map(self):  # 現在日時までのファイルをダウンロード
        logging.warning("JmaDownloader.download_map()")
        logging.warning(os.getcwd())
        logging.warning(self.map_name)
        while self.time_now <= self.time_end:
            logging.warning("{0}のダウンロード前です".format(self.time_now))
            self.download_file(self.time_now)
            # 日時を進める
            self.time_now += datetime.timedelta(minutes=self.interval)

    def download_file(self, time):  # 個々の画像を取得
        # 日時を文字列に変換
        time_str = time.strftime('%Y%m%d%H%M')
        # 画像名を指定
        file_name = os.path.join(self.map_name, self.map_name + '_' + time_str + '.png')
        # 画像が存在すれば何もしない
        if os.path.exists(file_name):
            return
        # URLの作成
        url = self.map_url + time_str + '-00.png'
        # ダウンロードする画像が存在する場合
        if file_is_on_server(url):
            while True:
                # ダウンロード試行
                try:
                    req = requests.get(url, timeout=10)
                # ダウンロードできない場合：
                except Exception as e:
                    print('[ダウンロードエラー] {0}'.format(e))
                    tm.sleep(10)
                # ダウンロードが成功したら画像を保存
                else:
                    with open(file_name, 'wb') as fp:
                        fp.write(req.content)
                    print('[ダウンロード] {0}'.format(file_name))
                    break

        # ダウンロードする画像が存在しない場合
        else:
            # interval分前の画像が存在する場合
            try:
                shutil.copy(os.path.join(self.map_name, self.map_name + '_' + (time - datetime.timedelta(minutes=self.interval)).strftime('%Y%m%d%H%M') + '.png'), file_name)
            # interval分前の画像が存在しない場合
            except FileNotFoundError:
                pass
            except Exception as e:
                exit_program(e, sys.exc_info())
            # コピーが成功したことを表示
            else:
                print('[コピー　　　] {0}'.format(file_name))


class JmaDownloaderWeatherMap(JmaDownloader):
    # 天気図ダウンロード用
    def __init__(self, map_name, map_url, interval):
        # 初期化
        super().__init__(map_name, map_url, interval)

    def download_file(self, time):  # 個々のファイルを取得
        # 日時を文字列に変換して調整
        time_str = time.strftime('%Y%m%d%H')
        time_str = time_str[2:]
        # ファイル名を取得
        file_name = os.path.join(self.map_name, self.map_name + '_' + time_str + '.png')
        # ファイルが存在すれば何もしない
        if os.path.exists(file_name):
            return
        # URLを作成
        url = self.map_url + time_str + '.png'
        # 0時のファイルを取得する場合
        if time_str[(len(time_str) - 2):] == '00':
            # 3時間前の日時を文字列に変換
            time_str_before = (time - datetime.timedelta(hours=3)).strftime('%Y%m%d%H')
            time_str_before = time_str_before[2:]
            # 3時間前の日時のファイル名を取得
            file_name_before = os.path.join(self.map_name, self.map_name + '_' + time_str_before + '.png')
            # 3時間前のファイルをが存在する場合
            try:
                shutil.copy(file_name_before, file_name)
            # 3時間前のファイルも存在しない場合
            except FileNotFoundError:
                pass
            except Exception as e:
                exit_program(e, sys.exc_info())
            # コピーが成功したことを表示
            else:
                print('[コピー　　　] {0}'.format(file_name))

        # 0時以外のファイルを取得する場合
        else:
            # ダウンロードしたいファイルがサーバーにある場合
            if (file_is_on_server(url)):
                while True:
                    # ダウンロード試行
                    try:
                        req = requests.get(url, timeout=10)
                    # ダウンロードできない場合
                    except Exception as e:
                        print(e)
                        tm.sleep(10)
                    # ダウンロード成功したらファイルを保存
                    else:
                        with open(file_name, "wb") as fp:
                            fp.write(req.content)
                        print('[ダウンロード] {0}'.format(file_name))
                        break

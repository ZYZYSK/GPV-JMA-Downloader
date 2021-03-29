###################################################################
# 気象衛星画像

###################################################################
import sys
import json
import urllib.request
import time
import requests
import numpy as np
import signal
import datetime
import cv2

from urllib3 import request
import urllib3
if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()

from .exit_program import *
from .file_is_on_server import *


class DownloadSatellite:
    def __init__(self):
        # 一時ファイルの名前
        self.tmp_name = "tmp_sat.jpg"
        # 設定ファイルの読み込み
        with open("settings_sat.json") as fp:
            self.settings = json.load(fp)
        # ファイルの保存場所に移動
        try:
            # ディレクトリが存在しなければ作成
            for dirs in self.settings["path"].values():
                os.makedirs(dirs, exist_ok=True)
        except Exception as e:
            exit_program(e, sys.exc_info())
        # 地図が存在しなければ作成して，開く
        self.image_map = self.draw_base(5, 25, 10, 30, 14, self.settings["path_map"]["j"])
        # 時刻リストを取得(日本域)
        self.jp_time_list = self.get_time_list("https://www.jma.go.jp/bosai/himawari/data/satimg/targetTimes_fd.json", "気象衛星画像")
        # 時刻表にのっていない時間
        self.time_end = datetime.datetime.strptime(self.jp_time_list[0]["basetime"], "%Y%m%d%H%M%S")
        self.time_begin = self.time_end - datetime.timedelta(days=7)

    def get_time_list(self, uri, text):  # 時刻リストを取得
        while True:
            try:
                with urllib.request.urlopen(uri) as fp:
                    time_list = json.load(fp)
            except Exception as e:
                print(f'[時刻リストの取得エラー] {e}')
                time.sleep(10)
            else:
                print(f'[時刻リストを取得({text})]')
                return time_list

    def download_jp_common(self, band, prod, z, x0, y0, x1, y1, path_dir, alpha=0.95, beta=0.05):  # ダウンロード(共通，日本域)
        for time_this in self.jp_time_list:
            # 保存先
            path = os.path.join(path_dir, f'{time_this["basetime"]}.jpg')
            self.draw_content(time_this["basetime"], time_this["validtime"], band, prod, z, x0, y0, x1, y1, path, check=False, alpha=alpha, beta=beta)
        # 時刻リストにのっていない古いデータをダウンロード
        time_this = self.time_begin
        while time_this < self.time_end:
            if time_this.hour % 12 != 2 and time_this.minute != 50:
                # 保存先
                basetime = time_this.strftime("%Y%m%d%H%M%S")
                path = os.path.join(path_dir, f'{basetime}.jpg')
                self.draw_content(basetime, basetime, band, prod, z, x0, y0, x1, y1, path, alpha=alpha, beta=beta)
            time_this += datetime.timedelta(minutes=10)

    def download_jp_infrared(self):  # ダウンロード(赤外画像,日本域)
        self.download_jp_common("B13", "TBB", 5, 25, 10, 30, 14, self.settings["path"]["jp_infrared"])

    def download_jp_visible(self):  # ダウンロード(可視画像,日本域)
        self.download_jp_common("B03", "ALBD", 5, 25, 10, 30, 14, self.settings["path"]["jp_visible"])

    def download_jp_watervapor(self):  # ダウンロード(水蒸気画像,日本域)
        self.download_jp_common("B08", "TBB", 5, 25, 10, 30, 14, self.settings["path"]["jp_watervapor"])

    def download_jp_truecolor(self):  # ダウンロード(トゥルーカラー再現画像,日本域)
        self.download_jp_common("REP", "ETC", 5, 25, 10, 30, 14, self.settings["path"]["jp_truecolor"], alpha=1, beta=0)

    def download_jp_cloudheight(self):  # ダウンロード(雲頂画像,日本域)
        self.download_jp_common("SND", "ETC", 5, 25, 10, 30, 14, self.settings["path"]["jp_cloudheight"])

    def draw_content(self, basetime, validtime, band, prod, z, x0, y0, x1, y1, path, check=True, alpha=0.95, beta=0.05):  # 画像描画
        # ファイルが存在するなら何もしない
        if not os.path.exists(path):
            image_list = np.empty((y1 - y0 + 1, x1 - x0 + 1), dtype=np.ndarray)
            # ダウンロード
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    uri = f'https://www.jma.go.jp/bosai/himawari/data/satimg/{basetime}/fd/{validtime}/{band}/{prod}/{str(z)}/{str(x)}/{str(y)}.jpg'
                    # 時刻リストにないファイルだけチェックする
                    if check and not file_is_on_server(uri):
                        print(f'[{basetime}] サーバにないファイルです')
                        return
                    image_list[y - y0][x - x0] = cv2.imread(self.download(uri, self.tmp_name))
            # 結合
            try:
                image = cv2.vconcat([cv2.hconcat(image_h) for image_h in image_list])
            except cv2.error:
                print(f'[{basetime}] 作成できませんでした')
            # マッピング
            image = cv2.addWeighted(src1=image, alpha=alpha, src2=self.image_map, beta=beta, gamma=0)
            # 文字書き込み
            date_utc = datetime.datetime.strptime(basetime, "%Y%m%d%H%M%S")
            date_jst = date_utc + datetime.timedelta(hours=9)
            date_str = f'{date_jst.strftime("%Y.%m.%d %H:%M")}JST ({date_utc.strftime("%Y.%m.%d %H:%M")}UTC)'
            cv2.putText(image, date_str, (10, 1270), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
            # 画像を保存
            cv2.imwrite(path, image)
            print(f'[{date_str}] {path}')

    def draw_base(self, z, x0, y0, x1, y1, path):  # 地図描画
        # ファイルが存在するなら何もしない
        if not os.path.exists(path):
            image_list = np.empty((y1 - y0 + 1, x1 - x0 + 1), dtype=np.ndarray)
            # ダウンロード
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    image_list[y - y0][x - x0] = cv2.imread(self.download(f'https://cyberjapandata.gsi.go.jp/xyz/gmld_ptc2/{str(z)}/{str(x)}/{str(y)}.png', self.tmp_name))
            # 結合
            image = cv2.vconcat([cv2.hconcat(image_h) for image_h in image_list])
            # 色を置換
            green = [0, 162, 0]
            blue_old = [220, 220, 90]
            blue = [255, 0, 0]
            image[np.where((image != blue_old).all(axis=2))] = green
            image[np.where((image == blue_old).all(axis=2))] = blue
            image[np.where(((image != green) & (image != blue_old)).all(axis=2))] = green
            # 画像を保存
            cv2.imwrite(path, image)
            print(f'[地図を作成] {path}')
        # 地図ファイルを開く
        return cv2.imread(path)

    @classmethod
    def download(cls, uri, path):  # ダウンロードしたファイルのパスを返す
        while True:
            try:
                req = requests.get(uri, timeout=10)
            # ダウンロードできない場合
            except Exception as e:
                print(f'[エラー　　　　] {e}')
                tm.sleep(10)
            # ダウンロードが成功したらファイルを保存
            else:
                with open(path, "wb") as fp:
                    fp.write(req.content)
                return path

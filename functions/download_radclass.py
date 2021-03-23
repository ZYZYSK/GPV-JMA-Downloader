###################################################################
# レーダー画像
###################################################################
import sys

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()

from .download_satclass import *


class DownloadRadar(DownloadSatellite):
    def __init__(self):
        # 一時ファイルの名前
        self.tmp_name = "tmp_rad.png"
        # 設定ファイルの読み込み
        with open("settings_rad.json") as fp:
            self.settings = json.load(fp)
        # ファイルの保存場所に移動
        try:
            # ディレクトリが存在しなければ作成
            for dirs in self.settings["path"].values():
                os.makedirs(dirs, exist_ok=True)
        except Exception as e:
            exit_program(e, sys.exc_info())
        # 地図が存在しなければ作成して，開く
        self.image_map = self.draw_base(6, 53, 22, 58, 27, self.settings["path_map"]["j"])
        # 凡例が存在しなければ取得して，追加
        self.draw_legend()
        # 時刻リストを取得(日本域)
        self.j_time_list = super().get_time_list("https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N1.json", "レーダー画像")
        # # 時刻表にのっていない時間
        self.time_end = datetime.datetime.strptime(self.j_time_list[-1]["basetime"], "%Y%m%d%H%M%S")
        self.time_begin = self.time_end - datetime.timedelta(days=4)

    def download_j_radar(self):  # ダウンロード(レーダー画像,日本域)
        for time_this in self.j_time_list:
            # 保存先
            path = os.path.join(self.settings["path"]["j_radar"], f'{time_this["basetime"]}.jpg')
            self.draw_content(time_this["basetime"], time_this["validtime"], 6, 53, 22, 58, 27, path, check=False)
        # 時刻リストにのっていない古いデータをダウンロード
        time_this = self.time_begin
        while time_this < self.time_end:
            # 保存先
            basetime = time_this.strftime("%Y%m%d%H%M%S")
            path = os.path.join(self.settings["path"]["j_radar"], f'{basetime}.jpg')
            # 画像作成
            self.draw_content(basetime, basetime, 6, 53, 22, 58, 27, path)
            time_this += datetime.timedelta(minutes=5)

    def draw_content(self, basetime, validtime, z, x0, y0, x1, y1, path, check=True, alpha=1, beta=1):  # 画像作成
        # ファイルが存在するなら何もしない
        if not os.path.exists(path):
            image_list = np.empty((y1 - y0 + 1, x1 - x0 + 1), dtype=np.ndarray)
            # ダウンロード
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    uri = f'https://www.jma.go.jp/bosai/jmatile/data/nowc/{basetime}/none/{validtime}/surf/hrpns/{str(z)}/{str(x)}/{str(y)}.png'
                    # 時刻リストにないファイルだけチェックする
                    if check and not file_is_on_server(uri):
                        print(f'[{basetime}] サーバにないファイルです')
                        return
                    image_list[y - y0][x - x0] = cv2.imread(super().download(uri, self.tmp_name), -1)
            # 結合
            image = cv2.vconcat([cv2.hconcat(image_h) for image_h in image_list])
            ###################################################################
            # マッピング
            ###################################################################
            # rgb成分を取り出す
            rgb = image[:, :, :3]
            rgb[np.where((rgb == [0, 0, 0]).all(axis=2))] = [255, 255, 255]
            # α成分を取り出す
            a = image[:, :, 3]
            # マスク画像を作成
            mask = cv2.merge((a, a, a))
            # マスク画像と合成
            dst = cv2.bitwise_or(self.image_map, mask)
            dst = cv2.bitwise_and(dst, rgb)

            # 文字書き込み
            date_utc = datetime.datetime.strptime(basetime, "%Y%m%d%H%M%S")
            date_jst = date_utc + datetime.timedelta(hours=9)
            date_str = f'{date_jst.strftime("%Y.%m.%d %H:%M")}JST ({date_utc.strftime("%Y.%m.%d %H:%M")}UTC)'
            cv2.putText(dst, date_str, (10, 1520), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4)
            # 画像を保存
            cv2.imwrite(path, dst)
            print(f'[{date_str}] {path}')

    def draw_base(self, z, x0, y0, x1, y1, path):  # 地図描画
        # ファイルが存在するなら何もしない
        if not os.path.exists(path):
            image_list = np.empty((y1 - y0 + 1, x1 - x0 + 1), dtype=np.ndarray)
            # ダウンロード
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    image_list[y - y0][x - x0] = cv2.imread(super().download(f'https://cyberjapandata.gsi.go.jp/xyz/gmld_ptc2/{str(z)}/{str(x)}/{str(y)}.png', self.tmp_name))
            # 結合
            image = cv2.vconcat([cv2.hconcat(image_h) for image_h in image_list])
            # 色を置換
            gray_continent = [150, 150, 150]
            gray_sea = [125, 125, 125]
            blue_old = [220, 220, 90]
            image[np.where((image != blue_old).all(axis=2))] = gray_continent
            image[np.where((image == blue_old).all(axis=2))] = gray_sea
            image[np.where(((image != gray_continent) & (image != gray_sea)).all(axis=2))] = gray_continent
            cv2.imwrite(path, image)
            print(f'[地図を作成] {path}')
        # 地図ファイルを開く
        return cv2.imread(path, -1)

    def draw_legend(self):  # 凡例のダウンロード
        # 凡例が存在しなければダウンロード
        if not os.path.exists(self.settings["path_legend"]):
            path = self.download("https://www.jma.go.jp/bosai/nowc/images/legend_jp_normal_hrpns.svg", f'{self.settings["path_legend"]}.svg')
            print(f'[凡例を取得] {path}')
            exit_program("pngファイルに変換してからもう一度実行してください")
        # 凡例を開く
        image_legend = cv2.imread(self.settings["path_legend"], -1)
        # 凡例追加部分を白色で塗りつぶし
        height, width = image_legend.shape[:2]
        rect = np.array([[1200, 1200], [1200, 1200 + height], [1200 + width, 1200 + height], [1200 + width, 1200]])
        self.image_map = cv2.fillPoly(self.image_map, pts=[rect], color=(255, 255, 255))
        # これをやらないと凡例の文字が表示されない
        image_legend[np.where((image_legend == [0, 0, 0, 0]).all(axis=2))] = [255, 255, 255, 0]
        # rgb成分を取り出す
        rgb = image_legend[:, :, :3]
        # α成分を取り出す
        a = image_legend[:, :, 3]
        # マスク画像を作成
        mask = cv2.merge((a, a, a))
        # 凡例を追加
        image_new = cv2.bitwise_or(self.image_map[rect[0, 1]:rect[2, 1], rect[0, 0]:rect[2, 0]], mask)
        image_new = cv2.bitwise_and(image_new, rgb)
        self.image_map[rect[0, 1]:rect[2, 1], rect[0, 0]:rect[2, 0]] = image_new

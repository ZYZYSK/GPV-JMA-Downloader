from .download_gsmclass import *

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()

from .exit_program import *
from .file_is_on_server import *


class DownloadMSM(DownloadGSM):
    # 図の範囲(日本域)
    extent_jp = [120, 150, 22.4, 47.6]

    def __init__(self, time_this, fig_x, fig_y, path):
        super().__init__(time_this, fig_x, fig_y, path)

    def __del__(self):
        return super().__del__()

    def download_grib2(self):
        # ダウンロード済みの場合は何もしない
        if not os.path.exists(self.path_grib2):
            # ダウンロード先URI
            uri_grib2 = f'http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/{self.time_this.strftime("%Y/%m/%d")}/Z__C_RJTD_{self.time_this.strftime("%Y%m%d%H%M%S")}_MSM_GPV_Rjp_Lsurf_FH00-15_grib2.bin'
            # ダウンロード試行
            self.download_grib2_sub(uri_grib2)
        self.grib2 = grib.open(self.path_grib2)

    def draw_map(self):  # 地図(日本域)を作成
        # 地図
        fig = plt.figure(figsize=(self.fig_x, self.fig_y))
        ax_jp = fig.add_subplot(1, 1, 1, projection=self.mapcrs_jp)
        # 地図の範囲を設定
        ax_jp.set_extent(self.extent_jp, self.datacrs)
        # 陸の塗りつぶし
        ax_jp.add_feature(cfeature.LAND, color='black', alpha=0.8)
        # 海の塗りつぶし
        ax_jp.add_feature(cfeature.OCEAN, color='black', alpha=0.8)
        # 海岸線を追加
        ax_jp.add_feature(cfeature.COASTLINE.with_scale('50m'), edgecolor='white', linewidth=2)
        # 格子線の大きさ、色、線種、間隔の設定(ここでは緯線と経線をひく)
        ax_jp.gridlines(xlocs=mticker.MultipleLocator(10),
                        ylocs=mticker.MultipleLocator(10),
                        linestyle=':', color='grey')
        return fig, ax_jp

    def colorbar_jp(self, cf):
        return super().colorbar_jp(cf)

    def grib2_select_jp(self, shortName):
        return self.grib2.select(shortName=shortName, forecastTime=0)[0].data()

    def jp_surf_ppc(self, path):  # 地上気圧/降水量/雲量(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 地上気圧，緯度，経度の取得
        pressure, lat, lon = self.grib2_select_jp("prmsl")
        pressure *= units('Pa')
        pressure /= 100
        # ガウシアンフィルター
        pressure = gaussian_filter(pressure, sigma=12.0)
        # 降水量の取得
        precipitation, _, _ = self.grib2.select(forecastTime=0)[10].data() * units('kg/m^2')
        # 雲量の取得
        tcc, _, _ = self.grib2.select(forecastTime=0)[9].data()
        # 地上風の取得
        wind_u, _, _ = self.grib2_select_jp('10u') * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('10v') * units('m/s')
        # 地図の描画
        fig, ax = self.draw_map()
        # 雲量の描画
        tcc_costant = ax.contourf(lon, lat, tcc, np.arange(0, 110, 10), cmap="gray", transform=self.datacrs, alpha=0.9)
        # カラーバーをつける(雲量)
        cbar = plt.colorbar(tcc_costant, orientation="vertical", fraction=0.15, shrink=0.95, aspect=20, pad=0)
        cbar.ax.tick_params(labelsize=super().fontsize)
        cbar.set_label('CLOUD COVER(%)', fontsize=super().fontsize)
        # カラーマップの作成(降水量)
        precipitation_colors = ["aliceblue"] * 1 + ["skyblue"] * 4 + ["dodgerblue"] * 5 + ["blue"] * 10 + ["yellow"] * 10 + ["orange"] * 20 + ["red"] * 30 + ["darkmagenta"] * 20
        precipitation_cmap = ListedColormap(precipitation_colors)
        # 降水量の描画
        precipitation_arange = np.array([0.1, 1, 5, 10, 20, 30, 50, 80, 100])
        precipitation_constant = ax.contourf(lon, lat, precipitation, precipitation_arange, extend="max", cmap=precipitation_cmap, transform=self.datacrs, alpha=0.9)
        # カラーバーをつける(降水量)
        cbar1 = self.draw_jp_colorbar(precipitation_constant)
        cbar1.set_label('PRECIPITATION(mm/h)', fontsize=super().fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 30), slice(None, None, 30))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m, wind_v[wind_arrow].to('kt').m, pivot='middle', color='green', alpha=0.9, transform=self.datacrs, length=10)
        # 等圧線を引く
        height_line = ax.contour(lon, lat, pressure, np.arange(900, 1600, 4), colors="red", transform=self.datacrs)
        plt.clabel(height_line, fontsize=super().fontsize, fmt="%d")
        # タイトルをつける
        self.draw_title(ax, 'SUFRACE: PRESSURE(hPa)\n PRECIPITATION(mm/h), CLOUD COVER(%)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 地上気圧/降水量/雲量(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def test(self):
        return super().test()

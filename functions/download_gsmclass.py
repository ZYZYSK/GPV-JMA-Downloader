import os
import shutil
import sys
import time as tm
import datetime
import requests
import signal
import json

import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.util as cutil
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import cm
from matplotlib.colors import ListedColormap
from metpy.units import units
import metpy.calc as mpcalc
from scipy.ndimage import gaussian_filter
import pygrib as grib

if __name__ == "__main__":
    print("please execute main.py")
    sys.exit()

from .exit_program import *
from .file_is_on_server import *


class DownloadGSM:
    ###################################################################
    # クラス変数
    ###################################################################
    # 時差
    time_diff = 9
    # 図の範囲(日本域)
    lat_min_jp = 0
    lat_max_jp = 70
    lon_min_jp = 60
    lon_max_jp = 200
    extent_jp = [100, 170, 10, 60]
    # 図の範囲(北極中心)
    lat_min_np = -10
    lat_max_np = 90
    extent_np = [-40, 320, 20, 90]
    # ランベルト正角円錐図法(日本域)
    mapcrs_jp = ccrs.LambertConformal(
        central_longitude=140, central_latitude=35, standard_parallels=(30, 60))
    # 正距方位図法(北極中心)
    mapcrs_np = ccrs.AzimuthalEquidistant(central_longitude=140, central_latitude=90)
    # 正距円筒図法
    datacrs = ccrs.PlateCarree()
    # 高度のシグマ
    height_sigma = 1.0
    # フォントサイズのデフォルト
    fontsize = 25

    def __init__(self, time_this, fig_x, fig_y, path):
        # 時間
        self.time_this = time_this
        self.time_str1 = time_this.strftime('%Y%m%d%H')
        self.time_str2 = f'{(time_this + datetime.timedelta(hours=self.time_diff)).strftime("%Y.%m.%d %H")}JST ({time_this.strftime("%Y.%m.%d %H")}UTC)'
        # 解像度x,y
        self.fig_x = fig_x
        self.fig_y = fig_y
        # ダウンロードするgrib2ファイルの保存先
        self.path_grib2 = os.path.join(path, time_this.strftime('%Y%m%d%H'))
        # grib2ファイル
        self.grib2 = None

    def __del__(self):
        # grib2ファイルを閉じる
        self.grib2.close()

    def download_grib2(self):  # grib2ファイルのダウンロード
        # ダウンロード済みの場合は何もしない
        if not os.path.exists(self.path_grib2):
            # ダウンロード先URI
            uri_grib2 = f'http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/original/{self.time_this.strftime("%Y/%m/%d")}/Z__C_RJTD_{self.time_this.strftime("%Y%m%d%H%M%S")}_GSM_GPV_Rgl_FD0000_grib2.bin'
            # ダウンロード試行
            self.download_grib2_sub(uri_grib2)
        self.grib2 = grib.open(self.path_grib2)

    def download_grib2_sub(self, uri_grib2):
        # ダウンロード試行
        while True:
            try:
                req = requests.get(uri_grib2, timeout=10)

            # ダウンロードできない場合
            except Exception as e:
                print(f'[エラー　　　] {e}')
                tm.sleep(10)

            # ダウンロードが成功したらファイルを保存
            else:
                with open(self.path_grib2, 'wb') as fp:
                    fp.write(req.content)
                print(f'[ダウンロード] {self.path_grib2}: {uri_grib2}')
                break

    def draw_map(self, projection, extent):  # 地図を描画
        # 地図
        fig = plt.figure(figsize=(self.fig_x, self.fig_y))
        ax = fig.add_subplot(1, 1, 1, projection=projection)
        # 地図の範囲を設定
        ax.set_extent(extent, self.datacrs)
        # 海岸線を追加
        ax.add_feature(cfeature.COASTLINE.with_scale('50m'))
        # 国境線を追加
        ax.add_feature(cfeature.BORDERS.with_scale('50m'))
        # 陸の塗りつぶし
        ax.add_feature(cfeature.LAND, color='black', alpha=0.8)
        # 格子線の大きさ、色、線種、間隔の設定(ここでは緯線と経線をひく)
        ax.gridlines(xlocs=mticker.MultipleLocator(10),
                     ylocs=mticker.MultipleLocator(10),
                     linestyle=':', color='grey')
        return fig, ax

    def draw_jp_colorbar(self, cf):  # カラーバー
        cbar = plt.colorbar(cf, orientation='horizontal', fraction=0.05, shrink=0.95, aspect=50, pad=0)
        cbar.ax.tick_params(labelsize=self.fontsize)
        return cbar

    def draw_title(self, ax, title_l, title_r):  # タイトルを描画
        ax.set_title(title_l, loc='left', fontsize=self.fontsize)
        ax.set_title(title_r, loc='right', fontsize=self.fontsize)

    def grib2_select_jp(self, shortName, level):  # grib2ファイルから指定したデータを取得(日本域)
        return self.grib2.select(shortName=shortName, level=level)[0].data(lat1=self.lat_min_jp, lat2=self.lat_max_jp, lon1=self.lon_min_jp, lon2=self.lon_max_jp)

    # grib2ファイルから指定したデータを取得(北極域)
    def grib2_select_np(self, shortName, level):
        return self.grib2.select(shortName=shortName, level=level)[0].data(lat1=self.lat_min_np, lat2=self.lat_max_np)

    def jp_300_hw(self, path):  # 300hPa高度/風(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 300hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 300)
        # ガウシアンフィルター
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 300hPa風の取得
        wind_u, _, _ = self.grib2_select_jp('u', 300) * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('v', 300) * units('m/s')
        wind_speed = mpcalc.wind_speed(wind_u, wind_v).to('kt')
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # 等風速線を引く
        wind_constant = ax.contourf(lon, lat, wind_speed, np.arange(0, 220, 20), extend='max', cmap='YlGnBu', transform=self.datacrs, alpha=0.9)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(wind_constant)
        cbar.set_label('ISOTECH(kt)', fontsize=self.fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m, wind_v[wind_arrow].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs, length=10)
        # 等高度線を引く
        height_line = ax.contour(lon, lat, height, np.arange(5400, 12000, 120), colors='black', transform=self.datacrs)
        plt.clabel(height_line, fmt='%d', fontsize=self.fontsize)
        # タイトルをつける
        self.draw_title(ax, '300hPa: HEIGHT(M), ISOTACH(kt), WIND ARROW(kt)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 300hPa高度/風(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_ht(self, path):  # 500hPa高度/気温(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 500hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 500)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 500hPa気温の取得
        temp, _, _ = self.grib2_select_jp('t', 500)
        temp = (temp * units.kelvin).to(units.celsius)
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # 温度の塗りつぶし
        temp_arange = np.arange(-48, 9, 3)
        temp_constant = ax.contourf(lon, lat, temp, temp_arange, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(temp_constant)
        cbar.set_label('TEMP($^\circ$C)', fontsize=self.fontsize)
        # 等温線
        temp_line = ax.contour(lon, lat, temp, temp_arange, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(temp_line, fontsize=self.fontsize, fmt='%d')
        # 等高度線
        height_line = ax.contour(lon, lat, height, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(height_line, fmt='%d', fontsize=self.fontsize)
        # タイトルをつける
        self.draw_title(ax, '500hPa: HEIGHT(M), TEMP($^\circ$C)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 500hPa高度/気温(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_hv(self, path):  # 500hPa高度/風/渦度(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 500hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 500)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 500hPa風の取得
        wind_u, _, _ = self.grib2_select_jp('u', 500) * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('v', 500) * units('m/s')
        # 渦度の計算
        vort_x, vort_y = mpcalc.lat_lon_grid_deltas(lon, lat)
        vort_abs = mpcalc.vorticity(wind_u, wind_v, vort_x, vort_y, dim_order='yx')
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # カラーマップを作成する
        N = 140
        M = 380
        PuBu = np.flipud(cm.get_cmap('BuPu', N)(range(N)))
        YlOrRd = cm.get_cmap('YlOrRd', M)(range(M))
        PuBuYlOrRd = ListedColormap(np.vstack((PuBu, YlOrRd)))
        # 等渦度線を引く
        vort_constant = ax.contourf(lon, lat, vort_abs * 10**6, np.arange(-120, 390, 30), extend='both', cmap=PuBuYlOrRd, transform=self.datacrs, alpha=0.9)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(vort_constant)
        cbar.set_label('VORT($10^{-6}/s$)', fontsize=self.fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m, wind_v[wind_arrow].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs, length=10)
        # 等高度線を引く
        height_line = ax.contour(lon, lat, height, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(height_line, fmt='%d', fontsize=self.fontsize)
        # タイトルをつける
        self.draw_title(ax, '500hPa: HEIGHT(M), WIND ARROW(kt), VORT($10^{-6}/s$)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 500hPa高度/風/渦度(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_t_700_td(self, path):  # 500hPa気温/700hPa湿数(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 500hPa気温、緯度、経度の取得
        temp, lat, lon = self.grib2_select_jp('t', 500)
        temp = (temp * units.kelvin).to(units.celsius)
        # 700hPa湿数の取得
        temp_700, _, _ = self.grib2_select_jp('t', 700) * units.kelvin
        rh, _, _ = self.grib2_select_jp('r', 700)
        rh *= 0.01
        dewp_700 = mpcalc.dewpoint_from_relative_humidity(temp_700, rh)
        td = temp_700 - dewp_700
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # カラーマップを作成する
        N = 256
        M_PuBu = np.flipud(cm.get_cmap('BuPu', N)(range(N)))
        PuBu = ListedColormap(M_PuBu)
        # 等湿数線を引く
        td_constant = ax.contourf(lon, lat, td, np.arange(0, 21, 3), extend='max', cmap=PuBu, transform=self.datacrs, alpha=0.9)
        td_line = ax.contour(lon, lat, td, np.array([-100, 3]), colors='yellow', linestyles='solid', transform=self.datacrs)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(td_constant)
        cbar.set_label('T-Td($^\circ$C)', fontsize=self.fontsize)
        # 等温線を引く
        temp_line = ax.contour(lon, lat, temp, np.arange(-60, 30, 3), colors='black', linestyles='solid', transform=self.datacrs)
        plt.clabel(temp_line, fontsize=self.fontsize, fmt='%d')
        # タイトルをつける
        self.draw_title(ax, '500hPa: TEMP($^\circ$C)\n700hPa: T-Td($^\circ$C)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 500hPa気温/700hPa湿数(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_ht(self, path):  # 850hPa高度/気温(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 850hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 850)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 850hPa気温の取得
        temp, _, _ = self.grib2_select_jp('t', 850)
        temp = (temp * units.kelvin).to(units.celsius)
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # 等温線を引く
        temp_arange = np.arange(-24, 33, 3)
        temp_constant = ax.contourf(lon, lat, temp, temp_arange, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        temp_line = ax.contour(lon, lat, temp, temp_arange, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(temp_line, fontsize=self.fontsize, fmt='%d')
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(temp_constant)
        cbar.set_label('TEMP($^\circ$C)', fontsize=self.fontsize)
        # 等高度線を引く
        height_line = ax.contour(lon, lat, height, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(height_line, fmt='%d', fontsize=self.fontsize)
        # タイトルをつける
        self.draw_title(ax, '850hPa: HEIGHT(M), TEMP($^\circ$C)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 850hPa高度/気温(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_tw_700_vv(self, path):  # 850hPa気温/風，700hPa上昇流(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 850hPa気温、緯度、経度の取得
        temp, lat, lon = self.grib2_select_jp('t', 850)
        temp = (gaussian_filter(temp, sigma=1.0) * units.kelvin).to(units.celsius)
        # 700hPa上昇流の取得
        vv, _, _ = self.grib2_select_jp('w', 700)
        vv = (vv * units.Pa / units.second).to(units.hPa / units.hour)
        # 850hPa風の取得
        wind_u, _, _ = self.grib2_select_jp('u', 850) * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('v', 850) * units('m/s')
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # カラーマップを作成する
        N = 125
        M = 65
        RdOrYl = np.flipud(cm.get_cmap('YlOrRd', N)(range(N)))
        BuPu = cm.get_cmap('BuPu', M)(range(M))
        RdOrYlBuPu = ListedColormap(np.vstack((RdOrYl, BuPu)))
        # 等上昇流線を引く
        vv_constant = ax.contourf(lon, lat, vv, np.arange(-120, 70, 10), extend='both', cmap=RdOrYlBuPu, transform=self.datacrs, alpha=0.9)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(vv_constant)
        cbar.set_label('VERTICAL VELOCITY(hPa/h)', fontsize=self.fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m, wind_v[wind_arrow].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs, length=10)
        # 等温線を引く
        temp_line = ax.contour(lon, lat, temp, np.arange(-60, 60, 3), colors='black', transform=self.datacrs)
        plt.clabel(temp_line, fontsize=self.fontsize, fmt='%d')
        # タイトルをつける
        self.draw_title(ax, '850hPa: HEIGHT(M), WIND ARROW(kt)\n700hPa: VERTICAL VELOCITY(hPa/h)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 850hPa気温/風，700hPa上昇流(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_eptw(self, path):  # 850hPa相当温位/風(日本域)

        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 850hPa気温の取得
        temp, lat, lon = self.grib2_select_jp('t', 850)
        temp = temp * units.kelvin
        # 850hPa風の取得
        wind_u, _, _ = self.grib2_select_jp('u', 850) * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('v', 850) * units('m/s')
        # 850hPa相対湿度の取得
        rh, _, _ = self.grib2_select_jp('r', 850)
        rh *= 0.01
        # 露点温度の計算
        dewp = mpcalc.dewpoint_from_relative_humidity(temp, rh)
        # 相当温位の計算
        ept = mpcalc.equivalent_potential_temperature(850 * units.hPa, temp, dewp)
        ept = gaussian_filter(ept, sigma=1.0)
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # 等温線を引く
        ept_arange = np.arange(255, 372, 3)
        ept_constant = ax.contourf(lon, lat, ept, ept_arange, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        ept_line = ax.contour(lon, lat, ept, ept_arange, colors='black', linestyles='solid', linewidths=1, transform=self.datacrs)
        plt.clabel(ept_line, levels=np.arange(258, 372, 6), fmt='%d', fontsize=self.fontsize)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(ept_constant)
        cbar.set_label('E.P.TEMP(K)', fontsize=self.fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 5), slice(None, None, 5))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m,
                 wind_v[wind_arrow].to('kt').m, pivot='middle', length=8, color='black', alpha=0.5, transform=self.datacrs)
        # タイトルをつける
        self.draw_title(ax, '850hPa: E.P.TEMP(K), WIND ARROW(kt)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 850hPa相当温位/風(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_surf_pwt(self, path):  # 地上気圧/風/気温（日本域）
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 地上気圧，緯度，経度の取得
        pressure, lat, lon = self.grib2_select_jp("prmsl", 0)
        pressure *= units('Pa')
        pressure /= 100
        # ガウシアンフィルター
        pressure = gaussian_filter(pressure, sigma=2.0)
        # 地上気温の取得
        temp, _, _ = self.grib2_select_jp("t", 1000)
        temp = (temp * units.kelvin).to(units.celsius)
        # 地上風の取得
        wind_u, _, _ = self.grib2_select_jp('10u', 10) * units('m/s')
        wind_v, _, _ = self.grib2_select_jp('10v', 10) * units('m/s')
        # 地図の描画
        fig, ax = self.draw_map(self.mapcrs_jp, self.extent_jp)
        # 等温線を引く
        temp_arange = np.arange(-15, 42, 3)
        temp_constant = ax.contourf(lon, lat, temp, temp_arange, extend="both", cmap="jet", transform=self.datacrs, alpha=0.9)
        temp_line = ax.contour(lon, lat, temp, temp_arange, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(temp_line, fontsize=20, fmt="%d")
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(temp_constant)
        cbar.set_label('TEMP($^\circ$C)', fontsize=self.fontsize)
        # 風ベクトルの表示
        wind_arrow = (slice(None, None, 5), slice(None, None, 5))
        ax.barbs(lon[wind_arrow], lat[wind_arrow], wind_u[wind_arrow].to('kt').m, wind_v[wind_arrow].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs, length=8)
        # 等圧線を引く
        cs = ax.contour(lon, lat, pressure, np.arange(900, 1600, 4), colors="black", transform=self.datacrs)
        plt.clabel(cs, fontsize=self.fontsize, fmt="%d")
        # タイトルをつける
        self.draw_title(ax, 'SUFRACE: PRESSURE(hPa), TEMP($^\circ$C), WIND ARROW(kt)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.05, top=0.95, left=0, right=1.0)
        # 保存
        print(f'[{self.time_str2}] 地上気圧/風/気温（日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def np_500_ht(self, path):  # 500hPa高度/気温(北極中心)
        path_fig = os.path.join(path, self.time_str1 + '.jpg')
        if(os.path.exists(path_fig)): return
        # 500hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_np('gh', 500)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 500hPa気温の取得
        temp, _, _ = self.grib2_select_np('t', 500)
        temp = (temp * units.kelvin).to(units.celsius)
        # Cyclic
        height_cyclic = np.empty((height.shape[0], height.shape[1] + 1))
        temp_cyclic = np.empty((temp.shape[0], temp.shape[1] + 1))
        lon_cyclic = np.empty((temp.shape[0], temp.shape[1] + 1))
        lat_cyclic = np.empty((temp.shape[0], temp.shape[1] + 1))
        for i in range(temp_cyclic.shape[0]):
            height_cyclic[i, :], lon_cyclic[i, :] = cutil.add_cyclic_point(height[i, :], coord=lon[i, :])
            temp_cyclic[i, :], lat_cyclic[i, :] = cutil.add_cyclic_point(temp[i, :], coord=lat[i, :])
        # 地図の描画
        old = self.fig_y
        self.fig_y = self.fig_x
        fig, ax = self.draw_map(self.mapcrs_np, self.extent_np)
        self.fig_y = old
        # 温度の塗りつぶし
        temp_arange = np.arange(-48, 9, 3)
        temp_constant = ax.contourf(lon_cyclic, lat_cyclic, temp_cyclic, temp_arange, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        # カラーバーをつける
        cbar = self.draw_jp_colorbar(temp_constant)
        cbar.set_label('TEMP($^\circ$C)', fontsize=self.fontsize)
        # 等温線
        temp_line = ax.contour(lon_cyclic, lat_cyclic, temp_cyclic, temp_arange, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(temp_line, levels=np.arange(-48, 9, 6), fontsize=self.fontsize, fmt='%d')
        # 等高度線
        height_line = ax.contour(lon_cyclic, lat_cyclic, height_cyclic, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(height_line, levels=np.arange(0, 8000, 120), fontsize=self.fontsize, fmt='%d')
        # タイトルをつける
        self.draw_title(ax, '500hPa: HEIGHT(M), TEMP($^\circ$C)', self.time_str2)
        # 大きさの調整
        plt.subplots_adjust(bottom=0.02, top=0.95, left=0.05, right=0.95)
        # 保存
        print(f'[{self.time_str2}] 500hPa高度/気温(北極中心)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def test(self):  # テスト用
        [print(self.grib2.message(i)) for i in range(1, 110)]
        print(self.grib2.select(forecastTime=0)[10].data())
        pressure, lat, lon = self.grib2_select_jp("prmsl", 0)

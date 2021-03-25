import os
import shutil
import sys
import time as tm
import datetime
import requests
from concurrent import futures
import signal
import json
from pathlib import Path

import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
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
    # ランベルト正角円錐図法(日本域)
    mapcrs_jp = ccrs.LambertConformal(
        central_longitude=140, central_latitude=35, standard_parallels=(30, 60))
    # 正距円筒図法
    datacrs = ccrs.PlateCarree()
    # 高度のシグマ
    height_sigma = 1.0

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
        self.grib2 = grib.open(self.path_grib2)

    def draw_map_jp(self):  # 地図(日本域)を作成
        # 地図
        ax_jp = plt.subplot(111, projection=self.mapcrs_jp)
        # 地図の範囲を設定
        ax_jp.set_extent(self.extent_jp, self.datacrs)
        # 海岸線を追加
        ax_jp.add_feature(cfeature.COASTLINE.with_scale('50m'))
        # 国境線を追加
        ax_jp.add_feature(cfeature.BORDERS.with_scale('50m'))
        # 陸の塗りつぶし
        ax_jp.add_feature(cfeature.LAND, color='black', alpha=0.8)
        # 格子線の大きさ、色、線種、間隔の設定(ここでは緯線と経線をひく)
        ax_jp.gridlines(xlocs=mticker.MultipleLocator(10),
                        ylocs=mticker.MultipleLocator(10),
                        linestyle=':', color='grey')
        return ax_jp

    def colorbar_jp(self, cf):  # カラーバー
        return plt.colorbar(cf, orientation='horizontal', fraction=0.05, shrink=0.95, aspect=100, pad=0)

    # grib2ファイルから指定したデータを取得
    def grib2_select_jp(self, shortName, level):
        return self.grib2.select(shortName=shortName, level=level)[0].data(lat1=self.lat_min_jp, lat2=self.lat_max_jp, lon1=self.lon_min_jp, lon2=self.lon_max_jp)

    def jp_300_hw(self, path):  # 300hPa高度/風(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 300hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 300)
        # ガウシアンフィルター
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 300hPa風の取得
        uwnd, _, _ = self.grib2_select_jp('u', 300) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('v', 300) * units('m/s')
        sped = mpcalc.wind_speed(uwnd, vwnd).to('kt')
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 等風速線を引く
        cf = ax.contourf(lon, lat, sped, np.arange(0, 220, 20), extend='max', cmap='YlGnBu', transform=self.datacrs, alpha=0.9)
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m, vwnd[wind_slice].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs)
        # 等高度線を引く
        cs = ax.contour(lon, lat, height, np.arange(5400, 12000, 120), colors='black', transform=self.datacrs)
        plt.clabel(cs, fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('WIND VELOCITY(kt)')
        # タイトルをつける
        plt.title('300hPa: HEIGHT(M), ISOTACH(kt)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 300hPa高度/風(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_ht(self, path):  # 500hPa高度/気温(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 500hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 500)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 500hPa気温の取得
        temp, _, _ = self.grib2_select_jp('t', 500)
        temp = (temp * units.kelvin).to(units.celsius)
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 温度の塗りつぶし
        clevs_temp = np.arange(-48, 9, 3)
        cf = ax.contourf(lon, lat, temp, clevs_temp, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        # 等温線
        cg = ax.contour(lon, lat, temp, clevs_temp, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(cg, levels=np.arange(-48, 9, 6), colors='black', fontsize=10, rightside_up=False, fmt='%d')
        # 等高度線
        cs = ax.contour(lon, lat, height, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(cs, levels=np.hstack((np.arange(0, 5700, 120), np.arange(5700, 6000, 60))), fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('TEMP($^\circ$C)')
        # タイトルをつける
        plt.title('500hPa: HEIGHT(M), TEMP($^\circ$C)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 500hPa高度/気温(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_hv(self, path):  # 500hPa高度/風/渦度(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 500hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 500)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 500hPa風の取得
        uwnd, _, _ = self.grib2_select_jp('u', 500) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('v', 500) * units('m/s')
        # 渦度の計算
        dx, dy = mpcalc.lat_lon_grid_deltas(lon, lat)
        avor = mpcalc.vorticity(uwnd, vwnd, dx, dy, dim_order='yx')
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # カラーマップを作成する
        N = 140
        M = 380
        PuBu = np.flipud(cm.get_cmap('BuPu', N)(range(N)))
        YlOrRd = cm.get_cmap('YlOrRd', M)(range(M))
        PuBuYlOrRd = ListedColormap(np.vstack((PuBu, YlOrRd)))
        # 等渦度線を引く
        clevs_vort = np.arange(-120, 380, 20)
        cf = ax.contourf(lon, lat, avor * 10**6, clevs_vort, extend='both', cmap=PuBuYlOrRd, transform=self.datacrs, alpha=0.9)
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m, vwnd[wind_slice].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs)
        # 等高度線を引く
        clevs_hght = np.arange(0, 8000, 60)
        cs = ax.contour(lon, lat, height, clevs_hght, colors='black', transform=self.datacrs)
        plt.clabel(cs, levels=np.hstack((np.arange(0, 5700, 120), np.arange(5700, 6000, 60))), fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('VORT($10^{-6}/s$)')
        # タイトルをつける
        plt.title('500hPa: HEIGHT(M), WIND ARROW(kt), VORT($10^{-6}/s$)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 500hPa高度/風/渦度(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_500_t_700_td(self, path):  # 500hPa気温/700hPa湿数(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
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
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # カラーマップを作成する
        N = 256
        M_PuBu = np.flipud(cm.get_cmap('BuPu', N)(range(N)))
        PuBu = ListedColormap(M_PuBu)
        # 等湿数線を引く
        clevs_td = np.arange(0, 21, 1)
        cf = ax.contourf(lon, lat, td, clevs_td, extend='both', cmap=PuBu, transform=self.datacrs, alpha=0.9)
        clevs_td2 = np.array([-100, 3])
        cg = ax.contour(lon, lat, td, clevs_td2, colors='yellow', linestyles='solid', transform=self.datacrs)
        # 等温線を引く
        clevs_temp = np.arange(-60, 30, 3)
        cs = ax.contour(lon, lat, temp, clevs_temp, colors='black', linestyles='solid', transform=self.datacrs)
        plt.clabel(cs, fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('T-Td($^\circ$C)')
        # タイトルをつける
        plt.title('500hPa: TEMP($^\circ$C)\n700hPa: T-Td($^\circ$C)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 500hPa気温/700hPa湿数(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_ht(self, path):  # 850hPa高度/気温(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 850hPa高度、緯度、経度の取得
        height, lat, lon = self.grib2_select_jp('gh', 850)
        height = gaussian_filter(height, sigma=self.height_sigma)
        # 850hPa気温の取得
        temp, _, _ = self.grib2_select_jp('t', 850)
        temp = (temp * units.kelvin).to(units.celsius)
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 等温線を引く
        clevs_temp = np.arange(-24, 33, 3)
        cf = ax.contourf(lon, lat, temp, clevs_temp, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        cg = ax.contour(lon, lat, temp, clevs_temp, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(cg, levels=np.arange(-24, 33, 6), colors='black', fontsize=10, rightside_up=False, fmt='%d')
        # 等高度線を引く
        cs = ax.contour(lon, lat, height, np.arange(0, 8000, 60), colors='black', transform=self.datacrs)
        plt.clabel(cs, fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('TEMP($^\circ$C)')
        # タイトルをつける
        plt.title('850hPa: HEIGHT(M), TEMP($^\circ$C)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 850hPa高度/気温(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_tw_700_vv(self, path):  # 850hPa気温/風，700hPa上昇流(日本域)
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 850hPa気温、緯度、経度の取得
        temp, lat, lon = self.grib2_select_jp('t', 850)
        temp = (gaussian_filter(temp, sigma=1.0) * units.kelvin).to(units.celsius)
        # 700hPa上昇流の取得
        vv, _, _ = self.grib2_select_jp('w', 700)
        vv = (vv * units.Pa / units.second).to(units.hPa / units.hour)
        # 850hPa風の取得
        uwnd, _, _ = self.grib2_select_jp('u', 850) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('v', 850) * units('m/s')
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # カラーマップを作成する
        N = 125
        M = 65
        RdOrYl = np.flipud(cm.get_cmap('YlOrRd', N)(range(N)))
        BuPu = cm.get_cmap('BuPu', M)(range(M))
        RdOrYlBuPu = ListedColormap(np.vstack((RdOrYl, BuPu)))
        # 等上昇流線を引く
        cf = ax.contourf(lon, lat, vv, np.arange(-120, 65, 5), extend='both', cmap=RdOrYlBuPu, transform=self.datacrs, alpha=0.9)
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 10), slice(None, None, 10))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m, vwnd[wind_slice].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs)
        # 等温線を引く
        cs = ax.contour(lon, lat, temp, np.arange(-60, 60, 3), colors='black', transform=self.datacrs)
        plt.clabel(cs, levels=np.arange(-60, 60, 6), fmt='%d')
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('VERTICAL VELOCITY(hPa/h)')
        # タイトルをつける
        plt.title('850hPa: HEIGHT(M), WIND ARROW(kt)\n700hPa: VERTICAL VELOCITY(hPa/h)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 850hPa気温/風，700hPa上昇流(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_850_eptw(self, path):  # 850hPa相当温位/風(日本域)

        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 850hPa気温の取得
        temp, lat, lon = self.grib2_select_jp('t', 850)
        temp = temp * units.kelvin
        # 850hPa風の取得
        uwnd, _, _ = self.grib2_select_jp('u', 850) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('v', 850) * units('m/s')
        # 850hPa相対湿度の取得
        rh, _, _ = self.grib2_select_jp('r', 850)
        rh *= 0.01
        # 露点温度の計算
        dewp = mpcalc.dewpoint_from_relative_humidity(temp, rh)
        # 相当温位の計算
        ept = mpcalc.equivalent_potential_temperature(850 * units.hPa, temp, dewp)
        ept = gaussian_filter(ept, sigma=1.0)
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 等温線を引く
        clevs_ept = np.arange(255, 372, 3)
        cf = ax.contourf(lon, lat, ept, clevs_ept, extend='both', cmap='jet', transform=self.datacrs, alpha=0.9)
        cg = ax.contour(lon, lat, ept, clevs_ept, colors='black', linestyles='solid', linewidths=1, transform=self.datacrs)
        plt.clabel(cg, levels=np.arange(258, 372, 6), fmt='%d')
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 5), slice(None, None, 5))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m,
                 vwnd[wind_slice].to('kt').m, pivot='middle', length=6, color='black', alpha=0.5, transform=self.datacrs)
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('E.P.TEMP(K)')
        # タイトルをつける
        plt.title('850hPa: E.P.TEMP(K), WIND ARROW(kt)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 850hPa相当温位/風(日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_surf_pwt(self, path):  # 地上気圧/風/気温（日本域）
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 地上気圧，緯度，経度の取得
        pressure, lat, lon = self.grib2_select_jp("prmsl", 0)
        pressure *= units('Pa')
        pressure /= 100
        # ガウシアンフィルター
        pressure = gaussian_filter(pressure, sigma=3.0)
        # 地上気温の取得
        temp, _, _ = self.grib2_select_jp("t", 1000)
        temp = (temp * units.kelvin).to(units.celsius)
        # 地上風の取得
        uwnd, _, _ = self.grib2_select_jp('10u', 10) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('10v', 10) * units('m/s')
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 等温線を引く
        clevs_temp = np.arange(-15, 42, 3)
        cf = ax.contourf(lon, lat, temp, clevs_temp, extend="both", cmap="jet", transform=self.datacrs, alpha=0.9)
        cg = ax.contour(lon, lat, temp, clevs_temp, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(cg, levels=np.arange(-15, 42, 6), colors="black", fontsize=10, rightside_up=False, fmt="%d")
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 5), slice(None, None, 5))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m, vwnd[wind_slice].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs)
        # 等圧線を引く
        cs = ax.contour(lon, lat, pressure, np.arange(900, 1600, 4), colors="black", transform=self.datacrs)
        plt.clabel(cs, fmt="%d")
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('TEMP($^\circ$C)')
        # タイトルをつける
        plt.title('GROUND: PRESSURE(hPa), TEMP($^\circ$C), WIND ARROW(kt)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 地上気圧/風/気温（日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def jp_surf_ppc(self, path):  # 地上気圧/降水量/雲量（日本域）
        path_fig = os.path.join(path, self.time_str1 + '.png')
        if(os.path.exists(path_fig)): return
        # 地上気圧，緯度，経度の取得
        pressure, lat, lon = self.grib2_select_jp("prmsl", 0)
        pressure *= units('Pa')
        pressure /= 100
        # ガウシアンフィルター
        pressure = gaussian_filter(pressure, sigma=3.0)
        # 雲量の取得

        # 地上気温の取得
        temp, _, _ = self.grib2_select_jp("2t", 2)
        temp = (temp * units.kelvin).to(units.celsius)
        # 地上風の取得
        uwnd, _, _ = self.grib2_select_jp('10u', 10) * units('m/s')
        vwnd, _, _ = self.grib2_select_jp('10v', 10) * units('m/s')
        # 図の数、大きさを設定
        fig = plt.figure(1, figsize=(self.fig_x, self.fig_y))
        # 地図の描画
        ax = self.draw_map_jp()
        # 等温線を引く
        clevs_temp = np.arange(-15, 42, 3)
        cf = ax.contourf(lon, lat, temp, clevs_temp, extend="both", cmap="jet", transform=self.datacrs, alpha=0.9)
        cg = ax.contour(lon, lat, temp, clevs_temp, colors='black', linestyles='dashed', alpha=0.5, transform=self.datacrs)
        plt.clabel(cg, levels=np.arange(-15, 42, 6), colors="black", fontsize=10, rightside_up=False, fmt="%d")
        # 風ベクトルの表示
        wind_slice = (slice(None, None, 5), slice(None, None, 5))
        ax.barbs(lon[wind_slice], lat[wind_slice], uwnd[wind_slice].to('kt').m, vwnd[wind_slice].to('kt').m, pivot='middle', color='black', alpha=0.5, transform=self.datacrs)
        # 等圧線を引く
        cs = ax.contour(lon, lat, pressure, np.arange(900, 1600, 4), colors="black", transform=self.datacrs)
        plt.clabel(cs, fmt="%d")
        # カラーバーをつける
        cbar = self.colorbar_jp(cf)
        cbar.set_label('TEMP($^\circ$C)')
        # タイトルをつける
        plt.title('GROUND: PRESSURE(hPa), TEMP($^\circ$C), WIND ARROW(kt)', loc='left')
        plt.title(self.time_str2, loc='right')
        # 大きさの調整
        plt.subplots_adjust(bottom=0.1, top=0.9)
        # 保存
        print(f'[{self.time_str2}] 地上気圧/風/気温（日本域)...{path_fig}'.format())
        plt.savefig(path_fig)
        # 閉じる
        plt.close(fig=fig)

    def test(self):  # テスト用
        [print(self.grib2.message(i)) for i in range(1, 110)]
        print(self.grib2.select(shortName="cp"))

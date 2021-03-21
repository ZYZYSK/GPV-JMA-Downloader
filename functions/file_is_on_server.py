import urllib
import time as tm


def file_is_on_server(url):  # インターネット接続を確認して，ダウンロードする対象がサーバーに存在するか確認
    def is_connected():
        while True:
            # ネット接続を確認
            try:
                urllib.request.urlopen('https://www.jma.go.jp/jma/index.html')
            # 接続できなければ10秒待って再試行
            except Exception as e:
                print('[接続エラー] {0}'.format(e))
                tm.sleep(10)
            # 接続出来たらループから抜ける
            else:
                break
    # 目的の画像がサーバーに存在するか確認
    #存在すればTrue, 存在しなければFalseを返す
    cnt = 0
    while cnt < 3:
        try:
            is_connected()
            urllib.request.urlopen(url)
        except Exception:
            cnt += 1
        else:
            return True
    return False

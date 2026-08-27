# agri_app

さつまいも・野菜の農作業記録アプリ。スマホから記録・閲覧でき、農薬・施肥・除草・天気のアドバイスを表示します。

## セットアップ(ローカル)

```powershell
cd agri_app
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

`.env.example` を参考に `.env` を作成するか、環境変数を設定してください。

```
APP_PASSWORD=好きなパスワード
SECRET_KEY=適当な文字列
```

## 起動

```powershell
$env:APP_PASSWORD="好きなパスワード"
.\venv\Scripts\python.exe app.py
```

`http://127.0.0.1:5000` にアクセス。同じWi-Fi内のスマホからは `http://<このPCのIPアドレス>:5000` でアクセスできます(Windowsファイアウォールでポート5000の受信許可が必要な場合があります)。

## 農薬データの取り込み

農薬アドバイス機能は、農林水産消費安全技術センター(FAMIC)が公開している「農薬登録情報提供システム」のデータを使用します。

1. https://www.acis.famic.go.jp/ddownload/ にアクセスし、利用規約に同意してCSV形式ファイル(ZIP)をダウンロード
2. ダウンロードしたZIPを展開し、中のCSVファイルを `agri_app/data/famic/` フォルダにそのまま置く
3. 以下を実行

```powershell
.\venv\Scripts\python.exe data\import_pesticides.py
```

- あらかじめアプリ内で作物を登録しておく必要があります(登録済みの作物名に一致する行だけを取り込みます)
- CSVの列名は配布時期によって変わることがあります。「列が見つかりません」と出た場合は `data/import_pesticides.py` 内の `BASE_COLUMNS` / `APPLICATION_COLUMNS` を実際のCSVのヘッダーに合わせて書き換えてください
- 商用利用には別途申請が必要です。個人利用の範囲でご使用ください

## 施肥ガイドの初期データ投入

```powershell
.\venv\Scripts\python.exe data\seed_fertilizer.py
```

さつまいも・パッションフルーツの参考データが登録されます。他の作物は、アプリ内の「施肥ガイドを管理」画面から追加できます。

## 主な機能

- 畑の複数登録(地図から座標を設定)
- 作物の登録、作業記録(写真最大4枚・作業時間・気温湿度自動記録)
- 作物ごとのタイムライン表示
- 農薬アドバイス(FAMICデータ)
- 施肥アドバイス
- 除草アドバイス(雑草の状態の推移+天気予報)
- 天気アドバイス(畑ごとの7日間予報、水やり・霜・高温・大雨の注意喚起)

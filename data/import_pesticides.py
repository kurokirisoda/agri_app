"""
FAMIC(農薬登録情報提供システム)からダウンロードしたCSVを取り込むスクリプト。

事前準備:
1. https://www.acis.famic.go.jp/ddownload/ で利用規約に同意し、CSV形式ファイル(ZIP)をダウンロード
2. ZIPを展開し、agri_app/data/famic/ フォルダにCSVをそのまま置く
3. 実行: python data/import_pesticides.py

ファイルは中身の列構成から「基本部」「適用部」を自動判別します。
列名が変わっている場合は BASE_COLUMNS / APPLICATION_COLUMNS を実際のCSVの
ヘッダーに合わせて書き換えてください。
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Crop, PesticideInfo

FAMIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "famic")

BASE_COLUMNS = {
    "registration_no": "登録番号",
    "pesticide_name": "農薬の名称",
}
APPLICATION_COLUMNS = {
    "registration_no": "登録番号",
    "category": "用途",
    "crop_name": "作物名",
    "target_pest": "適用病害虫雑草名",
    "usage_timing": "使用時期",
    "dilution": "希釈倍数使用量",
    "usage_count": "本剤の使用回数",
    "application_method": "使用方法",
}


def read_csv_any_encoding(path):
    for enc in ("cp932", "utf-8-sig", "utf-8"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"文字コードを判定できませんでした: {path}")


def classify_csv(rows):
    if not rows:
        return None
    header = rows[0].keys()
    if APPLICATION_COLUMNS["crop_name"] in header and APPLICATION_COLUMNS["target_pest"] in header:
        return "application"
    if BASE_COLUMNS["pesticide_name"] in header and "登録を有する者の名称" in header:
        return "base"
    return None


def main():
    with app.app_context():
        target_names = {c.pesticide_crop_name or c.name for c in Crop.query.all()}
        if not target_names:
            print("先にアプリで作物を登録してください。")
            return

        csv_paths = glob.glob(os.path.join(FAMIC_DIR, "*.csv"))
        if not csv_paths:
            print(f"{FAMIC_DIR} にCSVが見つかりません。READMEの手順でダウンロードしたZIPを展開して配置してください。")
            return

        base_rows = []
        application_rows = []
        for path in csv_paths:
            rows = read_csv_any_encoding(path)
            kind = classify_csv(rows)
            if kind == "base":
                base_rows.extend(rows)
            elif kind == "application":
                application_rows.extend(rows)

        if not base_rows or not application_rows:
            print("基本部・適用部のCSVを判別できませんでした。列名を確認してください。")
            return

        pesticide_names = {
            row[BASE_COLUMNS["registration_no"]]: row[BASE_COLUMNS["pesticide_name"]]
            for row in base_rows
        }

        PesticideInfo.query.delete()

        count = 0
        for row in application_rows:
            crop_name = row.get(APPLICATION_COLUMNS["crop_name"], "")
            if not any(t in crop_name for t in target_names):
                continue
            reg_no = row.get(APPLICATION_COLUMNS["registration_no"], "")
            info = PesticideInfo(
                registration_no=reg_no,
                pesticide_name=pesticide_names.get(reg_no, "(不明)"),
                crop_name=crop_name,
                category=row.get(APPLICATION_COLUMNS["category"], ""),
                target_pest=row.get(APPLICATION_COLUMNS["target_pest"], ""),
                usage_timing=row.get(APPLICATION_COLUMNS["usage_timing"], ""),
                dilution=row.get(APPLICATION_COLUMNS["dilution"], ""),
                usage_count=row.get(APPLICATION_COLUMNS["usage_count"], ""),
                application_method=row.get(APPLICATION_COLUMNS["application_method"], ""),
            )
            db.session.add(info)
            count += 1

        db.session.commit()
        print(f"{count} 件の農薬情報を取り込みました。")


if __name__ == "__main__":
    main()

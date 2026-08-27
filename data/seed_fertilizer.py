"""
初期の施肥ガイドデータを登録するスクリプト。
実行: python data/seed_fertilizer.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, FertilizerGuide

SEED_DATA = [
    {
        "crop_name": "さつまいも",
        "growth_stage": "基肥(元肥)を中心に全期間",
        "nitrogen": "3〜6kg",
        "phosphorus": "4〜8kg",
        "potassium": "8〜12kg",
        "note": (
            "窒素が多すぎると地上部ばかり茂って芋が肥大しない「つるぼけ」になりやすいので注意。"
            "窒素は生育初期〜中期に、リン酸は初期の根張りのために、カリは全期間吸収されるよう"
            "緩効性肥料や深層施肥の活用が効果的。堆肥との併用も有効。"
        ),
        "source": "日本いも類研究会 (https://www.jrt.gr.jp/q_a/spqa_sehi/)",
    },
    {
        "crop_name": "パッションフルーツ",
        "growth_stage": "元肥(植え付け2週間前)",
        "nitrogen": None,
        "phosphorus": None,
        "potassium": None,
        "note": (
            "1株あたりチッソ・リン酸・カリが8:8:8の配合肥料を150g、堆肥を10kg施用する目安"
            "(地植えの場合)。※公式の施肥基準ではなく、家庭栽培向けの実践的な目安です。"
        ),
        "source": "マイナビ農業 (https://agri.mynavi.jp/2024_08_24_276661/)",
    },
    {
        "crop_name": "パッションフルーツ",
        "growth_stage": "追肥(6月下旬〜、つる伸長期以降)",
        "nitrogen": None,
        "phosphorus": None,
        "potassium": None,
        "note": (
            "1株あたりぼかし肥料を75g施用。新しい蔓が伸び始めたら窒素分の多い肥料、"
            "葉が展開したらリン酸分の多い肥料に切り替え。開花期以降は2週間に1回リン酸肥料を施用。"
            "窒素過多だと葉ばかり茂って花芽が着きにくくなるので注意。"
            "※公式の施肥基準ではなく、家庭栽培向けの実践的な目安です。"
        ),
        "source": "マイナビ農業 (https://agri.mynavi.jp/2024_08_24_276661/)",
    },
]


def main():
    with app.app_context():
        added = 0
        for item in SEED_DATA:
            exists = FertilizerGuide.query.filter_by(
                crop_name=item["crop_name"], growth_stage=item["growth_stage"]
            ).first()
            if exists:
                continue
            db.session.add(FertilizerGuide(**item))
            added += 1
        db.session.commit()
        print(f"{added} 件の施肥ガイドを登録しました。")


if __name__ == "__main__":
    main()

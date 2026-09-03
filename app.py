from datetime import date, time as time_cls
from functools import wraps
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import or_

from config import Config
from models import db, Crop, WorkLog, WorkPhoto, PesticideInfo, Field, FertilizerGuide, WORK_TYPES
from weather import fetch_forecast, build_advice, fetch_day_conditions, build_weed_advice
from storage import save_photo

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()


@app.context_processor
def inject_version():
    return {"app_version": app.config.get("APP_VERSION")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.errorhandler(413)
def too_large(e):
    flash("アップロードできる写真の合計サイズを超えています。枚数を減らすかサイズを小さくして再度お試しください。")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == app.config["APP_PASSWORD"]:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("パスワードが違います")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


MAX_PHOTOS = 4


def _collect_photo_files(req):
    files = []
    camera_file = req.files.get("photo_camera")
    if camera_file and camera_file.filename:
        files.append(camera_file)
    for f in req.files.getlist("photos_gallery"):
        if f and f.filename:
            files.append(f)
    return files


def _parse_time(value):
    return time_cls.fromisoformat(value) if value else None


def _record_weather(log):
    field = log.field
    if not field:
        flash("畑が選択されていないため、気温・湿度は記録されませんでした。")
        return
    try:
        log.temperature, log.humidity = fetch_day_conditions(
            field.latitude, field.longitude, log.work_date, log.start_time, log.end_time
        )
    except requests.RequestException:
        flash("気象情報の取得に失敗しました。気温・湿度は記録されませんでした。")


@app.route("/")
@login_required
def dashboard():
    crop_list = Crop.query.order_by(Crop.name).all()
    return render_template("home.html", crops=crop_list)


@app.route("/logs")
@login_required
def all_logs():
    crop_id = request.args.get("crop_id", type=int)
    query = WorkLog.query.order_by(WorkLog.work_date.desc())
    if crop_id:
        query = query.filter_by(crop_id=crop_id)
    logs = query.limit(100).all()
    crops = Crop.query.order_by(Crop.name).all()
    return render_template("logs.html", logs=logs, crops=crops, selected_crop_id=crop_id)


@app.route("/crops", methods=["GET", "POST"])
@login_required
def crops():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            crop = Crop(
                name=name,
                variety=request.form.get("variety", "").strip() or None,
                note=request.form.get("note", "").strip() or None,
                pesticide_crop_name=request.form.get("pesticide_crop_name", "").strip() or None,
            )
            db.session.add(crop)
            db.session.commit()
            flash(f"「{name}」を登録しました")
            return redirect(url_for("crops"))
        flash("作物名を入力してください")
    crop_list = Crop.query.order_by(Crop.name).all()
    return render_template("crop_form.html", crops=crop_list)


@app.route("/crops/<int:crop_id>/edit", methods=["GET", "POST"])
@login_required
def edit_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            crop.name = name
            crop.variety = request.form.get("variety", "").strip() or None
            crop.note = request.form.get("note", "").strip() or None
            crop.pesticide_crop_name = request.form.get("pesticide_crop_name", "").strip() or None
            db.session.commit()
            flash(f"「{name}」を更新しました")
            return redirect(url_for("crops"))
        flash("作物名を入力してください")
    crop_list = Crop.query.order_by(Crop.name).all()
    return render_template("crop_form.html", crops=crop_list, edit_crop=crop)


@app.route("/crops/<int:crop_id>/delete", methods=["POST"])
@login_required
def delete_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    db.session.delete(crop)
    db.session.commit()
    flash(f"「{crop.name}」と関連する記録を削除しました")
    return redirect(url_for("crops"))


@app.route("/logs/new", methods=["GET", "POST"])
@login_required
def new_log():
    crop_list = Crop.query.order_by(Crop.name).all()
    if not crop_list:
        flash("先に作物を登録してください")
        return redirect(url_for("crops"))
    if request.method == "POST":
        start_time = _parse_time(request.form.get("start_time"))
        end_time = _parse_time(request.form.get("end_time"))
        log = WorkLog(
            crop_id=request.form.get("crop_id", type=int),
            field_id=request.form.get("field_id", type=int) or None,
            work_date=date.fromisoformat(request.form.get("work_date")),
            work_type=request.form.get("work_type"),
            start_time=start_time,
            end_time=end_time,
            pest_disease=request.form.get("pest_disease", "").strip() or None,
            weed_level=request.form.get("weed_level") or None,
            description=request.form.get("description", "").strip() or None,
        )
        db.session.add(log)
        db.session.flush()
        _record_weather(log)

        for f in _collect_photo_files(request)[:MAX_PHOTOS]:
            try:
                url = save_photo(
                    f, app.config.get("SUPABASE_URL"), app.config.get("SUPABASE_KEY"), app.config.get("SUPABASE_BUCKET")
                )
            except requests.RequestException as e:
                app.logger.error("Photo upload failed: %s", e)
                flash("写真の保存に失敗しました。他の項目は保存されています。")
                continue
            if url:
                db.session.add(WorkPhoto(work_log_id=log.id, photo_url=url))

        db.session.commit()
        flash("記録を保存しました")
        return redirect(url_for("crop_timeline", crop_id=log.crop_id))
    field_list = Field.query.order_by(Field.name).all()
    return render_template(
        "log_form.html", crops=crop_list, fields=field_list, work_types=WORK_TYPES,
        today=date.today().isoformat(), log=None, remaining_photo_slots=MAX_PHOTOS,
    )


@app.route("/logs/<int:log_id>")
@login_required
def log_detail(log_id):
    log = WorkLog.query.get_or_404(log_id)
    return render_template("log_detail.html", log=log)


@app.route("/logs/<int:log_id>/edit", methods=["GET", "POST"])
@login_required
def edit_log(log_id):
    log = WorkLog.query.get_or_404(log_id)
    crop_list = Crop.query.order_by(Crop.name).all()
    if request.method == "POST":
        log.crop_id = request.form.get("crop_id", type=int)
        log.field_id = request.form.get("field_id", type=int) or None
        log.work_date = date.fromisoformat(request.form.get("work_date"))
        log.work_type = request.form.get("work_type")
        log.start_time = _parse_time(request.form.get("start_time"))
        log.end_time = _parse_time(request.form.get("end_time"))
        log.pest_disease = request.form.get("pest_disease", "").strip() or None
        log.weed_level = request.form.get("weed_level") or None
        log.description = request.form.get("description", "").strip() or None
        _record_weather(log)

        remaining = max(MAX_PHOTOS - len(log.photos), 0)
        for f in _collect_photo_files(request)[:remaining]:
            try:
                url = save_photo(
                    f, app.config.get("SUPABASE_URL"), app.config.get("SUPABASE_KEY"), app.config.get("SUPABASE_BUCKET")
                )
            except requests.RequestException as e:
                app.logger.error("Photo upload failed: %s", e)
                flash("写真の保存に失敗しました。他の項目は保存されています。")
                continue
            if url:
                db.session.add(WorkPhoto(work_log_id=log.id, photo_url=url))

        db.session.commit()
        flash("記録を更新しました")
        return redirect(url_for("log_detail", log_id=log.id))
    field_list = Field.query.order_by(Field.name).all()
    return render_template(
        "log_form.html", crops=crop_list, fields=field_list, work_types=WORK_TYPES, today=log.work_date.isoformat(),
        log=log, remaining_photo_slots=max(MAX_PHOTOS - len(log.photos), 0),
    )


@app.route("/logs/<int:log_id>/delete", methods=["POST"])
@login_required
def delete_log(log_id):
    log = WorkLog.query.get_or_404(log_id)
    crop_id = log.crop_id
    db.session.delete(log)
    db.session.commit()
    flash("記録を削除しました")
    return redirect(url_for("crop_timeline", crop_id=crop_id))


@app.route("/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    photo = WorkPhoto.query.get_or_404(photo_id)
    log_id = photo.work_log_id
    db.session.delete(photo)
    db.session.commit()
    flash("写真を削除しました")
    return redirect(url_for("edit_log", log_id=log_id))


@app.route("/advice")
@login_required
def advice_select():
    crop_list = Crop.query.order_by(Crop.name).all()
    field_list = Field.query.order_by(Field.name).all()
    return render_template("advice_select.html", crops=crop_list, fields=field_list)


@app.route("/advice/pesticide/<int:crop_id>")
@login_required
def pesticide_advice(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    search_name = crop.pesticide_crop_name or crop.name
    query_kw = request.args.get("q", "").strip()
    has_data = PesticideInfo.query.first() is not None
    groups = []
    if has_data:
        q = PesticideInfo.query.filter(PesticideInfo.crop_name.contains(search_name))
        if query_kw:
            q = q.filter(PesticideInfo.target_pest.contains(query_kw))
        all_results = q.order_by(PesticideInfo.pesticide_name).all()

        grouped = {}
        for r in all_results:
            key = (r.category or "その他", r.target_pest or "")
            grouped.setdefault(key, []).append(r)

        for (category, target_pest), items in grouped.items():
            groups.append({
                "category": category,
                "target_pest": target_pest,
                "representative": items[0],
                "count": len(items),
            })
        groups.sort(key=lambda g: (g["category"], g["target_pest"]))
        groups = groups[:60]
    return render_template(
        "advice_result.html", crop=crop, groups=groups, query=query_kw, has_data=has_data
    )


@app.route("/fields", methods=["GET", "POST"])
@login_required
def fields():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        lat = request.form.get("latitude", type=float)
        lon = request.form.get("longitude", type=float)
        if not name or lat is None or lon is None:
            flash("畑の名前と座標を正しく入力してください")
        else:
            db.session.add(Field(name=name, latitude=lat, longitude=lon))
            db.session.commit()
            flash(f"「{name}」を登録しました")
            return redirect(url_for("fields"))
    field_list = Field.query.order_by(Field.name).all()
    return render_template("fields.html", fields=field_list)


@app.route("/fields/<int:field_id>/delete", methods=["POST"])
@login_required
def delete_field(field_id):
    field = Field.query.get_or_404(field_id)
    db.session.delete(field)
    db.session.commit()
    flash(f"「{field.name}」を削除しました")
    return redirect(url_for("fields"))


@app.route("/advice/weather/<int:field_id>")
@login_required
def weather_advice(field_id):
    field = Field.query.get_or_404(field_id)
    try:
        forecast = fetch_forecast(field.latitude, field.longitude)
        advice = build_advice(forecast)
        error = None
    except requests.RequestException:
        forecast, advice = [], []
        error = "天気予報の取得に失敗しました。しばらくしてから再度お試しください。"
    return render_template("weather_advice.html", field=field, forecast=forecast, advice=advice, error=error)


@app.route("/advice/fertilizer/<int:crop_id>")
@login_required
def fertilizer_advice(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    names = {crop.name}
    if crop.pesticide_crop_name:
        names.add(crop.pesticide_crop_name)
    conditions = [FertilizerGuide.crop_name.contains(n) for n in names]
    guides = FertilizerGuide.query.filter(or_(*conditions)).all()
    return render_template("fertilizer_advice.html", crop=crop, guides=guides)


@app.route("/fertilizer-guides", methods=["GET", "POST"])
@login_required
def fertilizer_guides():
    if request.method == "POST":
        guide = FertilizerGuide(
            crop_name=request.form.get("crop_name", "").strip(),
            growth_stage=request.form.get("growth_stage", "").strip() or None,
            nitrogen=request.form.get("nitrogen", "").strip() or None,
            phosphorus=request.form.get("phosphorus", "").strip() or None,
            potassium=request.form.get("potassium", "").strip() or None,
            note=request.form.get("note", "").strip() or None,
            source=request.form.get("source", "").strip() or None,
        )
        if guide.crop_name:
            db.session.add(guide)
            db.session.commit()
            flash("施肥ガイドを登録しました")
            return redirect(url_for("fertilizer_guides"))
        flash("作物名を入力してください")
    guides = FertilizerGuide.query.order_by(FertilizerGuide.crop_name).all()
    return render_template("fertilizer_guide_form.html", guides=guides)


@app.route("/fertilizer-guides/<int:guide_id>/delete", methods=["POST"])
@login_required
def delete_fertilizer_guide(guide_id):
    guide = FertilizerGuide.query.get_or_404(guide_id)
    db.session.delete(guide)
    db.session.commit()
    flash("削除しました")
    return redirect(url_for("fertilizer_guides"))


@app.route("/advice/weed/<int:crop_id>")
@login_required
def weed_advice(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    weed_records = (
        WorkLog.query.filter(WorkLog.crop_id == crop_id, WorkLog.weed_level.isnot(None))
        .order_by(WorkLog.work_date.desc(), WorkLog.id.desc())
        .limit(5)
        .all()
    )
    latest_field = next((r.field for r in weed_records if r.field), None)
    forecast = []
    if latest_field:
        try:
            forecast = fetch_forecast(latest_field.latitude, latest_field.longitude)
        except requests.RequestException:
            forecast = []
    advice = build_weed_advice(weed_records, forecast)
    return render_template("weed_advice.html", crop=crop, weed_records=weed_records, advice=advice)


@app.route("/crops/<int:crop_id>/timeline")
@login_required
def crop_timeline(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    field_id = request.args.get("field_id", type=int)
    query = WorkLog.query.filter_by(crop_id=crop_id)
    if field_id:
        query = query.filter_by(field_id=field_id)
    logs = query.order_by(WorkLog.work_date.asc(), WorkLog.id.asc()).all()
    field_list = Field.query.order_by(Field.name).all()
    return render_template(
        "timeline.html", crop=crop, logs=logs, fields=field_list, selected_field_id=field_id
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

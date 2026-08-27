from datetime import date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

WORK_TYPES = ["植え付け", "施肥", "防除", "除草", "かん水", "収穫", "その他"]


class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    variety = db.Column(db.String(50))
    note = db.Column(db.String(200))
    pesticide_crop_name = db.Column(db.String(50))
    logs = db.relationship("WorkLog", backref="crop", cascade="all, delete-orphan")


class WorkLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False, default=date.today)
    work_type = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pest_disease = db.Column(db.String(100))
    weed_level = db.Column(db.String(10))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    field_id = db.Column(db.Integer, db.ForeignKey("field.id"))
    field = db.relationship("Field", backref="logs")
    photos = db.relationship(
        "WorkPhoto", backref="work_log", cascade="all, delete-orphan", order_by="WorkPhoto.id"
    )


class WorkPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_log_id = db.Column(db.Integer, db.ForeignKey("work_log.id"), nullable=False)
    photo_url = db.Column(db.String(300), nullable=False)


class PesticideInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(20))
    pesticide_name = db.Column(db.String(100), nullable=False)
    crop_name = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(50))
    target_pest = db.Column(db.String(200))
    usage_timing = db.Column(db.String(200))
    dilution = db.Column(db.String(100))
    usage_count = db.Column(db.String(50))
    application_method = db.Column(db.String(100))


class Field(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)


class FertilizerGuide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(50), nullable=False, index=True)
    growth_stage = db.Column(db.String(50))
    nitrogen = db.Column(db.String(50))
    phosphorus = db.Column(db.String(50))
    potassium = db.Column(db.String(50))
    note = db.Column(db.Text)
    source = db.Column(db.String(200))

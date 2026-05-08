from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(40), default="created")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    images: Mapped[list["Image"]] = relationship(back_populates="analysis_run")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_run_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_runs.id"), nullable=True)
    image_name: Mapped[str] = mapped_column(String(255), index=True)
    image_path: Mapped[str] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[str | None] = mapped_column(String(80), nullable=True)

    analysis_run: Mapped[AnalysisRun | None] = relationship(back_populates="images")
    detections: Mapped[list["Detection"]] = relationship(back_populates="image")
    ocr_results: Mapped[list["OCRResultModel"]] = relationship(back_populates="image")


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"))
    detected_class: Mapped[str] = mapped_column(String(80), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    bbox_x1: Mapped[int] = mapped_column(Integer)
    bbox_y1: Mapped[int] = mapped_column(Integer)
    bbox_x2: Mapped[int] = mapped_column(Integer)
    bbox_y2: Mapped[int] = mapped_column(Integer)

    image: Mapped[Image] = relationship(back_populates="detections")


class Pole(Base):
    __tablename__ = "poles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source_image: Mapped[str] = mapped_column(String(255))
    pole_type: Mapped[str] = mapped_column(String(80))
    has_lamp: Mapped[bool] = mapped_column(Boolean, default=False)
    has_telecom_box: Mapped[bool] = mapped_column(Boolean, default=False)
    has_cable_loop: Mapped[bool] = mapped_column(Boolean, default=False)
    has_support: Mapped[bool] = mapped_column(Boolean, default=False)
    pole_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="auto_detected")


class OCRResultModel(Base):
    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"))
    text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[str] = mapped_column(String(120))

    image: Mapped[Image] = relationship(back_populates="ocr_results")

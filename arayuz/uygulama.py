"""Giriş noktası:  streamlit run arayuz/uygulama.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arayuz.bilesenler import sayfa  # noqa: E402

sayfa()

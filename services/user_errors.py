from __future__ import annotations
import logging
from typing import Literal
import streamlit as st
logger = logging.getLogger(__name__)
ErrorKind = Literal["connection", "classification", "database", "coach", "generic"]
_MESSAGES = {"connection": "Fehler beim Verbindungsaufbau. Bitte versuche es erneut.", "classification": "Die Trainingsklassifikation konnte momentan nicht durchgeführt werden. Bitte versuche es erneut.", "database": "Die Trainingsdaten konnten momentan nicht geladen werden. Bitte versuche es erneut.", "coach": "Das Coach-Feedback konnte momentan nicht erstellt werden. Bitte versuche es erneut.", "generic": "Es ist ein unerwarteter Fehler aufgetreten. Bitte versuche es erneut."}
def user_error(kind: ErrorKind, exc: Exception | None = None) -> str:
    if exc is not None: logger.exception("App-Fehler (%s)", kind, exc_info=exc)
    return _MESSAGES.get(kind, _MESSAGES["generic"])
def show_user_error(kind: ErrorKind, exc: Exception | None = None) -> None:
    st.warning(user_error(kind, exc))

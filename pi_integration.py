"""Pi SDK Streamlit component bridge."""
from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT = components.declare_component("pib2bnexus_pi", path=str(Path(__file__).parent / "pi_component"))

def render_pi_component(*, backend_url: str, app_session_token: str = "", payment_enabled: bool = False, payment_amount: float = 0.0, payment_memo: str = ""):
    return _COMPONENT(backend_url=backend_url, app_session_token=app_session_token, payment_enabled=payment_enabled, payment_amount=payment_amount, payment_memo=payment_memo, default=None, key="pib2bnexus_pi_component")

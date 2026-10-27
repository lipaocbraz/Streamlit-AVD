import pandas as pd
import streamlit as st


@st.cache_data(max_entries=1)
def load_data(path="data/clean/dataset.csv"):
    """Lê o dataset já tratado (exportado ao final do notebook de EDA)."""
    return pd.read_csv(path)

import io
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Business AI & Customer Alert",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📊 Pharma Business AI & Smart Customer Alert")
st.caption("Sales Excel upload karte hi churn & falling customers alert payein")

# Secrets se API Key
api_key = st.secrets.get("GEMINI_API_KEY", "")

# 1. File Uploader
uploaded_file = st.file_uploader(
    "📁 Sales Excel File Upload Karein (.xls / .xlsx)", type=["xls", "xlsx"]
)


def detect_customer_alerts(df):
  # Month columns detect karna
  numeric_cols = [
      c
      for c in df.columns
      if pd.to_numeric(df[c], errors="coerce").notnull().sum() > len(df) * 0.2
  ]
  if len(numeric_cols) < 2:
    return None, None

  # Customer column identify karna
  cust_col = next(
      (c for c in df.columns if "CUST" in c.upper() or "PARTY" in c.upper()),
      None,
  )
  if not cust_col:
    return None, None

  latest_month = numeric_cols[-1]
  past_months = numeric_cols[:-1]

  # Data clean & numeric conversion
  for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

  # Non-branch parties par focus (agar TYPE column ho)
  type_col = next((c for c in df.columns if "TYPE" in c.upper()), None)
  calc_df = (
      df[~df[type_col].astype(str).str.contains("BRANCH", case=False, na=False)]
      if type_col
      else df
  ).copy()

  calc_df["Past_Total"] = calc_df[past_months].sum(axis=1)
  calc_df["Past_Avg"] = calc_df[past_months].mean(axis=1)
  calc_df["Latest_Sale"] = calc_df[latest_month]

  # Alert 1: Churned (Past me acche the >= 50k total, ab bilkul ZERO sale)
  stopped = calc_df[
      (calc_df["Past_Total"] >= 50000) & (calc_df["Latest_Sale"] == 0)
  ].sort_values(by="Past_Total", ascending=False)

  # Alert 2: Declining (Past average >= 25k, par latest sale 50% se zyada gir gayi)
  declining = calc_df[
      (calc_df["Past_Avg"] >= 25000)
      & (calc_df["Latest_Sale"] > 0)
      & (calc_df["Latest_Sale"] < 0.5 * calc_df["Past_Avg"])
  ].copy()
  declining["Drop_%"] = (
      (declining["Past_Avg"] - declining["Latest_Sale"])
      / declining["Past_Avg"]
  ) * 100
  declining = declining.sort_values(by="Past_Avg", ascending=False)

  return stopped, declining, latest_month, past_months


if uploaded_file:
  try:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ File Loaded: {uploaded_file.name} ({len(df)} rows)")

    # --- CUSTOMER DROP / STOPPED SMART ALERT ---
    stopped_df, declining_df, latest_m, past_m = detect_customer_alerts(df)

    if stopped_df is not None and (len(stopped_df) > 0 or len(declining_df) > 0):
      st.error(
          "⚠️ **CRITICAL BUSINESS ALERT: In Customers Ki Taraf Dhyan Dein!**"
      )

      tab1, tab2 = st.tabs(
          ["🚨 Sale Poori Band Ho Gayi", "📉 Sale 50%+ Gir Rahi Hai"]
      )

      with tab1:
        st.markdown(
            f"**Ye aapke regular customers the jinka {latest_m} me Sale ZERO ho"
            " gaya hai:**"
        )
        display_stopped = stopped_df[
            [stopped_df.columns[1], "Past_Total", "Latest_Sale"]
        ].head(10)
        display_stopped.columns = [
            "Customer Name",
            "Pichla Total Sale (₹)",
            f"{latest_m} Sale (₹)",
        ]
        st.dataframe(
            display_stopped.style.format({
                "Pichla Total Sale (₹)": "₹{:,.2f}",
                f"{latest_m} Sale (₹)": "₹{:,.2f}",
            })
        )

      with tab2:
        st.markdown(
            f"**In customers ka sale past average ke mukable 50% se zyada gir"
            f" gaya hai:**"
        )
        display_declining = declining_df[
            [declining_df.columns[1], "Past_Avg", "Latest_Sale", "Drop_%"]
        ].head(10)
        display_declining.columns = [
            "Customer Name",
            "Past Monthly Avg (₹)",
            f"{latest_m} Sale (₹)",
            "Giraavat (%)",
        ]
        st.dataframe(
            display_declining.style.format({
                "Past Monthly Avg (₹)": "₹{:,.2f}",
                f"{latest_m} Sale (₹)": "₹{:,.2f}",
                "Giraavat (%)": "{:.1f}%",
            })
        )

    with st.expander("Data Preview Dekhein"):
      st.dataframe(df.head(5))

    # --- AI CHAT QUERY SECTION ---
    query = st.chat_input(
        "Poochiye: jaise 'Top 10 customer graph do' ya 'Declining customers ka"
        " excel export karo'"
    )

    if query:
      if not api_key:
        st.error("Kripya Streamlit Secrets mein GEMINI_API_KEY set karein!")
      else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-3.8-flash")

        schema_info = (
            f"Columns: {df.columns.tolist()}\nSample Data:\n{df.head(3).to_string()}"
        )

        prompt = f"""
                You are an expert Python Data Analyst. A pandas DataFrame named 'df' is already loaded.
                Dataset Info:
                {schema_info}

                User Query: {query}

                Write Python code using pandas and matplotlib to answer the request.
                Rules:
                - Do NOT reload dataset. Use existing 'df'.
                - If table/report is needed, save to variable 'result_df'.
                - If chart is needed, plot using matplotlib and assign the figure to variable 'fig'. Set large bold labels for mobile visibility.
                - Output ONLY pure python code inside ```python ``` block.
                """

        with st.spinner("AI Report analyze kar raha hai..."):
          response = model.generate_content(prompt)
          code = (
              response.text.replace("```python", "").replace("```", "").strip()
          )

          local_vars = {"df": df, "plt": plt, "pd": pd, "np": np}
          exec(code, {}, local_vars)

          if "result_df" in local_vars:
            st.subheader("📋 Generated Report")
            st.dataframe(local_vars["result_df"])

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
              local_vars["result_df"].to_excel(writer, index=False)
            st.download_button(
                label="📥 Download Report as Excel",
                data=output.getvalue(),
                file_name="ai_report.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )

          if "fig" in local_vars:
            st.subheader("📈 Generated Graph")
            st.pyplot(local_vars["fig"])

  except Exception as e:
    st.error(f"Error: {e}")

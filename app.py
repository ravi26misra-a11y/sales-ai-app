import io
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Business AI & Operator Follow-Up",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📊 Pharma Sales AI: Operator Follow-Up & Churn Alert")
st.caption(
    "Month-wise, Week-wise ya Day-wise sale upload karein aur Operator-wise"
    " Churn analysis payein"
)

# Secrets se API Key
api_key = st.secrets.get("GEMINI_API_KEY", "")

# 1. File Uploader
uploaded_file = st.file_uploader(
    "📁 Sales File Upload Karein (.xls / .xlsx)", type=["xls", "xlsx"]
)


def analyze_sales_trend(df):
  # Data cleaning
  cleaned_df = df.copy()

  # First 2 columns: Operator and Customer
  op_col = cleaned_df.columns[0]
  cust_col = cleaned_df.columns[1]

  cleaned_df[op_col] = (
      cleaned_df[op_col].astype(str).str.replace("\x00", "").str.strip()
  )
  cleaned_df[cust_col] = (
      cleaned_df[cust_col].astype(str).str.replace("\x00", "").str.strip()
  )

  # Remaining columns are Time periods (Month, Week or Day)
  time_cols = list(cleaned_df.columns[2:])

  for col in time_cols:
    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce").fillna(0)

  total_periods = len(time_cols)
  if total_periods < 2:
    return None, None, None, op_col, cust_col, time_cols

  # Dynamic split: agar 6 se zyada columns hain (e.g. week/day), recent = last 2 periods, warna last 1 period
  recent_k = 2 if total_periods >= 6 else 1
  past_cols = time_cols[:-recent_k]
  recent_cols = time_cols[-recent_k:]

  cleaned_df["Past_Avg"] = cleaned_df[past_cols].mean(axis=1)
  cleaned_df["Past_Total"] = cleaned_df[past_cols].sum(axis=1)
  cleaned_df["Recent_Avg"] = cleaned_df[recent_cols].mean(axis=1)
  cleaned_df["Recent_Total"] = cleaned_df[recent_cols].sum(axis=1)

  # Alert 1: Poori tarah band (Past Total >= 20,000 aur Recent Total == 0)
  stopped = cleaned_df[
      (cleaned_df["Past_Total"] >= 20000) & (cleaned_df["Recent_Total"] == 0)
  ].sort_values(by="Past_Total", ascending=False)

  # Alert 2: Sale 50%+ gir gayi (Past Avg >= 3,000, Recent > 0 par Recent Avg < 0.5 * Past Avg)
  declining = cleaned_df[
      (cleaned_df["Past_Avg"] >= 3000)
      & (cleaned_df["Recent_Avg"] > 0)
      & (cleaned_df["Recent_Avg"] < 0.5 * cleaned_df["Past_Avg"])
  ].copy()
  declining["Drop_%"] = (
      (declining["Past_Avg"] - declining["Recent_Avg"]) / declining["Past_Avg"]
  ) * 100
  declining = declining.sort_values(by="Past_Avg", ascending=False)

  return (
      cleaned_df,
      stopped,
      declining,
      op_col,
      cust_col,
      past_cols,
      recent_cols,
  )


if uploaded_file:
  try:
    df = pd.read_excel(uploaded_file)
    st.success(
        f"✅ File Loaded: {uploaded_file.name} ({len(df)} Parties, {len(df.columns) - 2} Time Periods)"
    )

    result = analyze_sales_trend(df)
    if result[0] is not None:
      (
          cleaned_df,
          stopped_df,
          declining_df,
          op_col,
          cust_col,
          past_cols,
          recent_cols,
      ) = result

      st.markdown("---")
      # --- OPERATOR FILTER ---
      operators = ["🌟 ALL OPERATORS (POORI COMPANY)"] + sorted(
          [op for op in cleaned_df[op_col].unique() if op and op != "nan"]
      )
      selected_op = st.selectbox(
          "👤 **Follow Up Operator Chunein:**", operators
      )

      # Filter according to selected operator
      if selected_op != "🌟 ALL OPERATORS (POORI COMPANY)":
        f_stopped = stopped_df[stopped_df[op_col] == selected_op]
        f_declining = declining_df[declining_df[op_col] == selected_op]
      else:
        f_stopped = stopped_df
        f_declining = declining_df

      # --- ALERT CARD & TABS ---
      st.error(
          f"🚨 **ATTENTION ALERT ({selected_op}):** In parties ka past record"
          " kaafi achha raha hai par ab sale drop/band ho rahi hai!"
      )

      col1, col2 = st.columns(2)
      col1.metric("🚨 Sale Poori Band Hui Parties", len(f_stopped))
      col2.metric("📉 50%+ Giraavat Wali Parties", len(f_declining))

      tab1, tab2 = st.tabs(
          ["🛑 Sale Bilkul Band (₹0)", "📉 Sale Me Badi Giraavat (50%+)"]
      )

      with tab1:
        if len(f_stopped) > 0:
          st.write(
              f"Ye parties pehle active theen, par pichhle {len(recent_cols)}"
              " period(s) mein inki billing ZERO ho chuki hai:"
          )
          show_stopped = f_stopped[
              [op_col, cust_col, "Past_Total", "Recent_Total"]
          ].copy()
          show_stopped.columns = [
              "Follow Up By",
              "Customer Name",
              "Pichla Total Sale (₹)",
              "Recent Sale (₹)",
          ]
          st.dataframe(
              show_stopped.style.format({
                  "Pichla Total Sale (₹)": "₹{:,.2f}",
                  "Recent Sale (₹)": "₹{:,.2f}",
              }),
              use_container_width=True,
          )

          # Export Stopped
          out1 = io.BytesIO()
          with pd.ExcelWriter(out1, engine="openpyxl") as w:
            show_stopped.to_excel(w, index=False)
          st.download_button(
              "📥 Download Zero Sale List (Excel)",
              out1.getvalue(),
              "zero_sale_parties.xlsx",
          )
        else:
          st.success("Is operator ke under koi badi party band nahi hui hai.")

      with tab2:
        if len(f_declining) > 0:
          st.write(
              f"In parties ka sale past average ke mukable **50% se zyada gir"
              " gaya hai**:"
          )
          show_dec = f_declining[
              [op_col, cust_col, "Past_Avg", "Recent_Avg", "Drop_%"]
          ].copy()
          show_dec.columns = [
              "Follow Up By",
              "Customer Name",
              "Past Avg Sale (₹)",
              "Recent Avg Sale (₹)",
              "Drop (%)",
          ]
          st.dataframe(
              show_dec.style.format({
                  "Past Avg Sale (₹)": "₹{:,.2f}",
                  "Recent Avg Sale (₹)": "₹{:,.2f}",
                  "Drop (%)": "{:.1f}%",
              }),
              use_container_width=True,
          )

          # Export Declining
          out2 = io.BytesIO()
          with pd.ExcelWriter(out2, engine="openpyxl") as w:
            show_dec.to_excel(w, index=False)
          st.download_button(
              "📥 Download Declining List (Excel)",
              out2.getvalue(),
              "declining_sale_parties.xlsx",
          )
        else:
          st.success("Is operator ke under koi badi giraavat nahi dikhi.")

    with st.expander("🔍 Raw Data Preview"):
      st.dataframe(df.head(5))

    st.markdown("---")
    # --- AI NATURAL QUERY CHAT ---
    query = st.chat_input(
        "Poochiye: jaise 'Archana ke top 5 parties ka graph do' ya"
        " 'Overall weekly trend batao'"
    )

    if query:
      if not api_key:
        st.error("Kripya Streamlit Secrets mein GEMINI_API_KEY set karein!")
      else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-3.8-flash")

        schema_info = (
            f"Columns: {df.columns.tolist()}\nFirst Column: Follow up"
            f" operator\nSecond Column: Customer\nRemaining columns: Time"
            f" periods\nSample Data:\n{df.head(3).to_string()}"
        )

        prompt = f"""
                You are a Senior Pharma Sales Data Analyst. A pandas DataFrame named 'df' is loaded.
                Dataset Info:
                {schema_info}

                User Query: {query}

                Write Python code using pandas and matplotlib to answer the request.
                Rules:
                - Do NOT reload dataset. Use existing 'df'.
                - If table/report is needed, save to variable 'result_df'.
                - If chart is needed, plot using matplotlib and assign the figure to variable 'fig'. Set large bold labels for mobile screen visibility.
                - Output ONLY pure python code inside ```python ``` block.
                """

        with st.spinner("AI Analysis kar raha hai..."):
          response = model.generate_content(prompt)
          code = (
              response.text.replace("```python", "").replace("```", "").strip()
          )

          local_vars = {"df": df, "plt": plt, "pd": pd, "np": np}
          exec(code, {}, local_vars)

          if "result_df" in local_vars:
            st.subheader("📋 AI Report")
            st.dataframe(local_vars["result_df"])

          if "fig" in local_vars:
            st.subheader("📈 AI Visual Graph")
            st.pyplot(local_vars["fig"])

  except Exception as e:
    st.error(f"Error: {e}")

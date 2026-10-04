import io
import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Business AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📊 Pharma Business AI")
st.caption("Sales, Outstanding ya koi bhi Excel upload karein aur sawaal poochein")

# Secrets se API Key lena
api_key = st.secrets.get("GEMINI_API_KEY", "")

# 1. File Uploader
uploaded_file = st.file_uploader(
    "📁 Excel File Upload Karein (.xls / .xlsx)", type=["xls", "xlsx"]
)

if uploaded_file:
  try:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ File Uploaded: {uploaded_file.name} ({len(df)} rows)")

    with st.expander("Data Preview Dekhein"):
      st.dataframe(df.head(5))

    # 2. Chat Input
    query = st.chat_input(
        "Poochiye: jaise 'Top 10 party report' ya 'Branch sale graph'"
    )

    if query:
      if not api_key:
        st.error("Kripya Streamlit Secrets mein GEMINI_API_KEY set karein!")
      else:
        genai.configure(api_key=api_key)

        # Updated model name
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        schema_info = (
            f"Columns: {df.columns.tolist()}\nSample Data:\n{df.head(3).to_string()}"
        )

        prompt = f"""
                You are a Python Data Analyst. A pandas DataFrame named 'df' is already loaded.
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

          local_vars = {"df": df, "plt": plt, "pd": pd}
          exec(code, {}, local_vars)

          # Table display
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

          # Graph display
          if "fig" in local_vars:
            st.subheader("📈 Generated Graph")
            st.pyplot(local_vars["fig"])

  except Exception as e:
    st.error(f"Error: {e}")

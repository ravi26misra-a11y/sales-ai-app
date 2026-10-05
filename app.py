import io
import os
from datetime import datetime
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Business - Sales & Follow-Up Portal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- SECRETS & GITHUB PERMANENT STORAGE SETUP ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
gh_token = st.secrets.get("GH_TOKEN", "")
gh_repo_name = st.secrets.get("GH_REPO", "ravi26misra-a11y/sales-ai-app")
DB_FILE = "task_actions.csv"


def get_github_repo():
  if gh_token:
    try:
      from github import Github

      g = Github(gh_token)
      return g.get_repo(gh_repo_name)
    except Exception:
      pass
  return None


def clean_tasks_df(df_t):
  text_cols = [
      "Operator",
      "Customer",
      "Admin_Instruction",
      "Status",
      "Operator_Reason",
      "Action_Taken",
      "Reply_Date",
  ]
  for col in text_cols:
    if col in df_t.columns:
      df_t[col] = df_t[col].fillna("").astype(str)
  if "Task_ID" in df_t.columns:
    df_t["Task_ID"] = (
        pd.to_numeric(df_t["Task_ID"], errors="coerce").fillna(0).astype(int)
    )
  return df_t


def load_tasks():
  repo = get_github_repo()
  if repo:
    try:
      contents = repo.get_contents(DB_FILE)
      csv_data = contents.decoded_content.decode("utf-8")
      df_t = pd.read_csv(io.StringIO(csv_data))
      return clean_tasks_df(df_t)
    except Exception:
      pass

  if os.path.exists(DB_FILE):
    try:
      df_t = pd.read_csv(DB_FILE)
      return clean_tasks_df(df_t)
    except Exception:
      pass

  return pd.DataFrame(
      columns=[
          "Task_ID",
          "Date",
          "Operator",
          "Customer",
          "Admin_Instruction",
          "Status",
          "Operator_Reason",
          "Action_Taken",
          "Reply_Date",
      ]
  )


def save_tasks(df_tasks):
  csv_buffer = io.StringIO()
  df_tasks.to_csv(csv_buffer, index=False)
  csv_content = csv_buffer.getvalue()

  df_tasks.to_csv(DB_FILE, index=False)

  repo = get_github_repo()
  if repo:
    try:
      try:
        contents = repo.get_contents(DB_FILE)
        repo.update_file(
            DB_FILE,
            "Update task actions permanent sync",
            csv_content,
            contents.sha,
        )
      except Exception:
        repo.create_file(DB_FILE, "Initial task actions create", csv_content)
    except Exception as e:
      st.error(f"GitHub Sync Error: {e}")


# --- USER AUTHENTICATION / LOGIN ---
USERS = {
    "admin": {"password": "2619", "role": "ADMIN", "name": "Admin"},
    "archana": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOW UP BY ARCHANA (ARCHAN)",
    },
    "gagan": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOW UP BY GAGAN (GAGAN)",
    },
    "kavita": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOW UP BY KAVITA (KAVITA)",
    },
    "misra": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOW UP BY MISRA (UNDER)",
    },
    "sarfar": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOW UP BY SARFAR (SARFAR)",
    },
    "upadhyay": {
        "password": "123",
        "role": "OPERATOR",
        "name": "FOLLOWUPBY UPADHYAY (UPAD)",
    },
}

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["username"] = ""
  st.session_state["role"] = ""
  st.session_state["operator_name"] = ""


def login_screen():
  st.title("🔐 Pharma Portal Login")
  st.caption("Sales Monitoring, Team Follow-Up & AI Analytics")

  c1, c2, c3 = st.columns([1, 2, 1])
  with c2:
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")
    if st.button("🚀 Login", use_container_width=True):
      if username in USERS and USERS[username]["password"] == password:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.session_state["role"] = USERS[username]["role"]
        st.session_state["operator_name"] = USERS[username]["name"]
        st.rerun()
      else:
        st.error("Galat Username ya Password!")


# --- MAIN APP LOGIC ---
if not st.session_state["logged_in"]:
  login_screen()
else:
  st.sidebar.markdown(f"### 👤 Logged in: **{st.session_state['username'].upper()}**")
  st.sidebar.caption(f"Role: {st.session_state['role']}")
  if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

  # =========================================================================
  # 👑 ADMIN PANEL
  # =========================================================================
  if st.session_state["role"] == "ADMIN":
    st.title("👑 Admin Control & Sales Action Portal")

    uploaded_file = st.file_uploader(
        "📁 Sales File Upload Karein (.xls / .xlsx)", type=["xls", "xlsx"]
    )
    df = None

    admin_tab1, admin_tab2 = st.tabs([
        "📊 Sales Trend & Multi-Party Assign",
        "📋 Operator Follow-up Status (Responses)",
    ])

    with admin_tab1:
      if uploaded_file:
        df = pd.read_excel(uploaded_file)
        op_col = df.columns[0]
        cust_col = df.columns[1]
        time_cols = list(df.columns[2:])

        df[op_col] = df[op_col].astype(str).str.replace("\x00", "").str.strip()
        df[cust_col] = (
            df[cust_col].astype(str).str.replace("\x00", "").str.strip()
        )
        for c in time_cols:
          df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Dynamic Trend calculation
        recent_k = 2 if len(time_cols) >= 6 else 1
        past_cols = time_cols[:-recent_k]
        recent_cols = time_cols[-recent_k:]

        df["Past_Avg"] = df[past_cols].mean(axis=1).round(0).astype(int)
        df["Recent_Avg"] = df[recent_cols].mean(axis=1).round(0).astype(int)
        df["Past_Total"] = df[past_cols].sum(axis=1).round(0).astype(int)
        df["Recent_Total"] = df[recent_cols].sum(axis=1).round(0).astype(int)

        operators_list = sorted(
            [op for op in df[op_col].unique() if op and op != "nan"]
        )
        selected_op = st.selectbox("1️⃣ Operator Select Karein:", operators_list)

        op_data = df[df[op_col] == selected_op]
        critical_parties = op_data[
            ((op_data["Past_Total"] >= 15000) & (op_data["Recent_Total"] == 0))
            | (
                (op_data["Past_Avg"] >= 2000)
                & (op_data["Recent_Avg"] < 0.5 * op_data["Past_Avg"])
            )
        ].copy()

        st.warning(
            f"⚠️️ **{selected_op}** ke under **{len(critical_parties)}** parties"
            " critical hain (Sale gir rahi hai ya ₹0 ho chuki hai)."
        )

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
          exclude_assigned = st.checkbox(
              "🚫 Pehle se assign ki hui parties list se hatayein (Exclude"
              " Assigned)",
              value=True,
          )
        with col_opt2:
          show_all = st.checkbox(
              "Sabhi parties dekhna chahte hain (Sirf critical nahi)?",
              value=False,
          )

        target_df = op_data.copy() if show_all else critical_parties.copy()

        # Already assigned parties ko hatana
        existing_tasks = load_tasks()
        if exclude_assigned and len(existing_tasks) > 0:
          assigned_names = existing_tasks["Customer"].str.strip().unique()
          target_df = target_df[~target_df[cust_col].isin(assigned_names)]

        party_list = target_df[cust_col].tolist()

        if len(party_list) > 0:
          default_selection = (
              party_list[:3] if len(party_list) >= 3 else party_list
          )
          selected_parties = st.multiselect(
              f"2️⃣ Ek saath ek se zyada Parties select karein ({len(party_list)} available):",
              options=party_list,
              default=default_selection,
          )

          if selected_parties:
            st.write(f"**Selected ({len(selected_parties)}) Parties:**")
            preview_subset = target_df[
                target_df[cust_col].isin(selected_parties)
            ][[
                cust_col,
                "Past_Avg",
                "Recent_Avg",
                "Past_Total",
                "Recent_Total",
            ]].copy()

            preview_subset.columns = [
                "Customer Name",
                "Past Avg Sale (₹)",
                "Recent Avg Sale (₹)",
                "Past Total Sale (₹)",
                "Recent Total Sale (₹)",
            ]
            st.table(
                preview_subset.style.format({
                    "Past Avg Sale (₹)": "₹{:,.0f}",
                    "Recent Avg Sale (₹)": "₹{:,.0f}",
                    "Past Total Sale (₹)": "₹{:,.0f}",
                    "Recent Total Sale (₹)": "₹{:,.0f}",
                })
            )

          instruction = st.text_area(
              "3️⃣ Selected sabhi parties ke liye Operator ko Instruction bhejein:",
              value=(
                  "In parties ka sale record pehle achha tha par ab giraavat aayi"
                  " hai / band ho gaya hai. Kripya party se turant baat karein,"
                  " reason pata karein aur sale revive karne ke liye action"
                  " report submit karein."
              ),
          )

          if st.button(
              f"🚀 Send Task for All Selected ({len(selected_parties)}) Parties to"
              f" {selected_op}",
              type="primary",
          ):
            if len(selected_parties) == 0:
              st.error("Kripya kam se kam ek party select karein!")
            else:
              df_tasks = load_tasks()
              new_entries = []
              start_id = (
                  int(df_tasks["Task_ID"].max()) + 1
                  if len(df_tasks) > 0 and "Task_ID" in df_tasks.columns
                  else 1
              )

              for idx, p in enumerate(selected_parties):
                new_entries.append({
                    "Task_ID": int(start_id + idx),
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Operator": str(selected_op),
                    "Customer": str(p),
                    "Admin_Instruction": str(instruction),
                    "Status": "PENDING",
                    "Operator_Reason": "",
                    "Action_Taken": "",
                    "Reply_Date": "",
                })

              df_tasks = pd.concat(
                  [df_tasks, pd.DataFrame(new_entries)], ignore_index=True
              )
              save_tasks(df_tasks)
              st.success(
                  f"✅ Sabhi {len(selected_parties)} parties ke tasks successfully assign aur permanent save kar diye gaye!"
              )
              st.rerun()
        else:
          st.info(
              "Is filter ke mutabiq koi nayi party nahi bachi (Sabhi parties pehle se assign ho chuki hain ya koi critical party nahi hai)."
          )
      else:
        st.info("Pehle upar se Sales Excel file upload karein.")

    with admin_tab2:
      st.subheader("📋 Operator Follow-up Tracker & Custom Filter")
      tasks = load_tasks()

      if len(tasks) > 0:
        # --- DROPDOWN FILTERS FOR EVERY HEADING ---
        st.markdown("##### 🔍 Field-wise Filters (Apni Marzi Se Filter Karein):")
        f_col1, f_col2, f_col3 = st.columns(3)

        with f_col1:
          op_filter_list = ["ALL OPERATORS"] + sorted(
              [op for op in tasks["Operator"].unique() if str(op).strip()]
          )
          chosen_op = st.selectbox("👤 Operator Filter:", op_filter_list)

        with f_col2:
          status_filter_list = ["ALL STATUS"] + sorted(
              [s for s in tasks["Status"].unique() if str(s).strip()]
          )
          chosen_status = st.selectbox("📌 Status Filter:", status_filter_list)

        with f_col3:
          date_filter_list = ["ALL DATES"] + sorted(
              [d for d in tasks["Date"].unique() if str(d).strip()],
              reverse=True,
          )
          chosen_date = st.selectbox("📅 Date Filter:", date_filter_list)

        search_cust = st.text_input(
            "🏢 Customer Name Search (Optional):",
            placeholder="Type party name...",
        ).strip()

        # Apply Filters
        filtered_tasks = tasks.copy()
        if chosen_op != "ALL OPERATORS":
          filtered_tasks = filtered_tasks[filtered_tasks["Operator"] == chosen_op]
        if chosen_status != "ALL STATUS":
          filtered_tasks = filtered_tasks[
              filtered_tasks["Status"] == chosen_status
          ]
        if chosen_date != "ALL DATES":
          filtered_tasks = filtered_tasks[filtered_tasks["Date"] == chosen_date]
        if search_cust:
          filtered_tasks = filtered_tasks[
              filtered_tasks["Customer"].str.contains(search_cust, case=False, na=False)
          ]

        st.caption(
            f"Showing {len(filtered_tasks)} of {len(tasks)} Total Records"
        )
        st.table(filtered_tasks)

        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
          filtered_tasks.to_excel(w, index=False)
        st.download_button(
            "📥 Download Filtered Report Excel",
            out.getvalue(),
            "filtered_sales_actions.xlsx",
        )
      else:
        st.info("Abhi tak koi task assign nahi hua hai.")

    # --- AI CHAT QUERY AT BOTTOM ---
    if df is not None:
      st.markdown("---")
      st.subheader("💬 AI Analyst Chat Box (Data Par Sawaal Poochein)")
      query = st.chat_input("Poochiye: jaise 'Top 5 parties ka bar chart banao'")

      if query:
        if not api_key:
          st.error("Kripya Streamlit Secrets mein GEMINI_API_KEY set karein!")
        else:
          genai.configure(api_key=api_key)
          model = genai.GenerativeModel("models/gemini-3.8-flash")

          schema_info = (
              f"Columns: {df.columns.tolist()}\nFirst col: Follow Up By\nSecond"
              f" col: Customer\nRemaining: Sales periods\nSample"
              f" Data:\n{df.head(3).to_string()}"
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
                    - If chart is needed, plot using matplotlib and assign the figure to variable 'fig'. Set large bold labels for mobile visibility.
                    - Round all currency and sales figures to nearest integer (no decimal points).
                    - Output ONLY pure python code inside ```python ``` block.
                    """

          with st.spinner("AI Analysis kar raha hai..."):
            try:
              response = model.generate_content(prompt)
              code = (
                  response.text.replace("```python", "")
                  .replace("```", "")
                  .strip()
              )

              local_vars = {"df": df, "plt": plt, "pd": pd, "np": np}
              exec(code, {}, local_vars)

              if "result_df" in local_vars:
                st.subheader("📋 AI Generated Table")
                st.table(local_vars["result_df"])

              if "fig" in local_vars:
                st.subheader("📈 AI Generated Graph")
                st.pyplot(local_vars["fig"])
            except Exception as e:
              st.error(f"Chat analysis error: {e}")

  # =========================================================================
  # 👷 OPERATOR PANEL
  # =========================================================================
  elif st.session_state["role"] == "OPERATOR":
    op_name = st.session_state["operator_name"]
    st.title(f"👷 Operator Workspace: {st.session_state['username'].title()}")
    st.info(f"Assigned Profile: **{op_name}**")

    tasks = load_tasks()
    my_tasks = (
        tasks[tasks["Operator"] == op_name].copy()
        if len(tasks) > 0
        else pd.DataFrame()
    )

    if len(my_tasks) == 0:
      st.success("🎉 Shabaash! Aapke liye abhi koi pending inquiry nahi hai.")
    else:
      pending_tasks = my_tasks[my_tasks["Status"] == "PENDING"]
      completed_tasks = my_tasks[my_tasks["Status"] == "REPLIED"]

      tab_pending, tab_done = st.tabs([
          f"🚨 Pending Follow-Ups ({len(pending_tasks)})",
          f"✅ Completed Responses ({len(completed_tasks)})",
      ])

      with tab_pending:
        if len(pending_tasks) > 0:
          task_options = [
              f"Task #{row['Task_ID']} - {row['Customer']}"
              for _, row in pending_tasks.iterrows()
          ]
          selected_task_label = st.selectbox(
              "Select Party to Submit Report:", task_options
          )
          task_id = int(
              selected_task_label.split(" - ")[0].replace("Task #", "")
          )
          current_task = pending_tasks[
              pending_tasks["Task_ID"] == task_id
          ].iloc[0]

          st.error(
              f"📌 **Admin Instruction:** {current_task['Admin_Instruction']}"
          )
          st.caption(f"Assigned Date: {current_task['Date']}")

          with st.form("operator_response_form"):
            reason = st.text_area(
                "1. Sale Kam Hone / Band Hone Ka Reason (Party Se Baat Karke):",
                placeholder=(
                    "e.g., Competitor ka rate kam tha / Payment issue tha /"
                    " Stock dump tha..."
                ),
            )
            action = st.text_area(
                "2. Sale Wapas Badhane Ke Liye Kya Action Liya / Negotiation"
                " Kiya:",
                placeholder=(
                    "e.g., Party ko 1% extra discount offer kiya / Kal subah"
                    " order dene ka promise kiya..."
                ),
            )
            submit_btn = st.form_submit_button(
                "📤 Submit Response to Admin", type="primary"
            )

            if submit_btn:
              if reason.strip() and action.strip():
                mask = tasks["Task_ID"] == task_id
                tasks["Status"] = tasks["Status"].astype(object)
                tasks["Operator_Reason"] = tasks["Operator_Reason"].astype(
                    object
                )
                tasks["Action_Taken"] = tasks["Action_Taken"].astype(object)
                tasks["Reply_Date"] = tasks["Reply_Date"].astype(object)

                tasks.loc[mask, "Status"] = "REPLIED"
                tasks.loc[mask, "Operator_Reason"] = str(reason)
                tasks.loc[mask, "Action_Taken"] = str(action)
                tasks.loc[mask, "Reply_Date"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                )

                save_tasks(tasks)
                st.success("✅ Response submit ho gaya! Admin ko update dikhegi.")
                st.rerun()
              else:
                st.warning("Kripya Reason aur Action dono fields bharein!")
        else:
          st.success("Aapke saare pending inquiries solve ho chuke hain!")

      with tab_done:
        if len(completed_tasks) > 0:
          st.table(
              completed_tasks[[
                  "Task_ID",
                  "Customer",
                  "Operator_Reason",
                  "Action_Taken",
                  "Reply_Date",
              ]]
          )
        else:
          st.write("Abhi tak koi response submit nahi hua hai.")

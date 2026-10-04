from datetime import datetime
import io
import os
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Business - Sales & Follow-Up Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DATABASE SETUP (Permanent Tracking) ---
DB_FILE = "task_actions.csv"


def load_tasks():
  if os.path.exists(DB_FILE):
    return pd.read_csv(DB_FILE)
  else:
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
  df_tasks.to_csv(DB_FILE, index=False)


# --- USER AUTHENTICATION / LOGIN ---
USERS = {
    "admin": {
        "password": "123",
        "role": "ADMIN",
        "name": "Admin",
    },  # Aap password badal sakte hain
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


# Login Function
def login_screen():
  st.title("🔐 Pharma Portal Login")
  st.caption("Sales Monitoring & Action Tracking System")

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
  # Sidebar Logout
  st.sidebar.markdown(f"### 👤 Logged in as: **{st.session_state['username'].upper()}**")
  st.sidebar.caption(f"Role: {st.session_state['role']}")
  if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

  # =========================================================================
  # 👑 ADMIN PANEL
  # =========================================================================
  if st.session_state["role"] == "ADMIN":
    st.title("👑 Admin Control & Sales Action Portal")

    admin_tab1, admin_tab2 = st.tabs([
        "📊 Sales Trend & Assign Tasks",
        "📋 Operator Follow-up Status (Responses)",
    ])

    with admin_tab1:
      uploaded_file = st.file_uploader(
          "📁 Sales File Upload Karein (.xls / .xlsx)", type=["xls", "xlsx"]
      )
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

        df["Past_Avg"] = df[past_cols].mean(axis=1)
        df["Recent_Avg"] = df[recent_cols].mean(axis=1)
        df["Past_Total"] = df[past_cols].sum(axis=1)
        df["Recent_Total"] = df[recent_cols].sum(axis=1)

        # Filter Operator
        operators_list = sorted(
            [op for op in df[op_col].unique() if op and op != "nan"]
        )
        selected_op = st.selectbox("1️⃣ Operator Select Karein:", operators_list)

        # Operator-wise critical parties
        op_data = df[df[op_col] == selected_op]
        critical_parties = op_data[
            ((op_data["Past_Total"] >= 15000) & (op_data["Recent_Total"] == 0))
            | (
                (op_data["Past_Avg"] >= 2000)
                & (op_data["Recent_Avg"] < 0.5 * op_data["Past_Avg"])
            )
        ].copy()

        st.warning(
            f"⚠️ **{selected_op}** ke under total **{len(critical_parties)}**"
            " parties ka sale gira ya zero ho gaya hai."
        )

        # Select Party to take action
        if len(critical_parties) > 0:
          party_list = critical_parties[cust_col].tolist()
          selected_party = st.selectbox(
              "2️⃣ Kis Party ke baare mein inquiry karni hai?", party_list
          )

          party_info = critical_parties[
              critical_parties[cust_col] == selected_party
          ].iloc[0]
          c1, c2 = st.columns(2)
          c1.metric("Pichhla Record", f"₹{party_info['Past_Avg']:,.2f} /period")
          c2.metric("Current Status", f"₹{party_info['Recent_Avg']:,.2f}")

          # Action instruction form
          instruction = st.text_area(
              "3️⃣ Operator ke liye Hidayat / Instruction:",
              value=(
                  f"Please check why sale dropped for {selected_party}. Contact"
                  " party immediately and report reason and revival action."
              ),
          )

          if st.button("🚀 Send Instruction to Operator", type="primary"):
            df_tasks = load_tasks()
            new_task = {
                "Task_ID": len(df_tasks) + 1,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Operator": selected_op,
                "Customer": selected_party,
                "Admin_Instruction": instruction,
                "Status": "PENDING",
                "Operator_Reason": "",
                "Action_Taken": "",
                "Reply_Date": "",
            }
            df_tasks = pd.concat(
                [df_tasks, pd.DataFrame([new_task])], ignore_index=True
            )
            save_tasks(df_tasks)
            st.success(
                f"✅ Instruction successfully bhej di gayi: {selected_op} ko"
                f" {selected_party} ke liye!"
            )
        else:
          st.success("Is operator ke under sabhi parties ka trend achha hai!")

    with admin_tab2:
      st.subheader("📋 Operator Follow-up Tracker & Responses")
      tasks = load_tasks()
      if len(tasks) > 0:
        st.dataframe(tasks, use_container_width=True)

        # Export report
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
          tasks.to_excel(w, index=False)
        st.download_button(
            "📥 Download Action Tracker Excel", out.getvalue(), "sales_actions.xlsx"
        )
      else:
        st.info("Abhi tak koi task assign nahi kiya gaya hai.")

  # =========================================================================
  # 👷 OPERATOR PANEL
  # =========================================================================
  elif st.session_state["role"] == "OPERATOR":
    op_name = st.session_state["operator_name"]
    st.title(f"👷 Operator Workspace: {st.session_state['username'].title()}")
    st.info(f"Assigned Profile: **{op_name}**")

    tasks = load_tasks()
    # Operator ke apne tasks filter karna
    my_tasks = tasks[tasks["Operator"] == op_name].copy()

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
          task_id = int(selected_task_label.split(" - ")[0].replace("Task #", ""))
          current_task = pending_tasks[
              pending_tasks["Task_ID"] == task_id
          ].iloc[0]

          st.error(f"📌 **Admin Instruction:** {current_task['Admin_Instruction']}")
          st.caption(f"Assigned Date: {current_task['Date']}")

          # Operator response form
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
                tasks.loc[tasks["Task_ID"] == task_id, "Status"] = "REPLIED"
                tasks.loc[tasks["Task_ID"] == task_id, "Operator_Reason"] = (
                    reason
                )
                tasks.loc[tasks["Task_ID"] == task_id, "Action_Taken"] = action
                tasks.loc[tasks["Task_ID"] == task_id, "Reply_Date"] = (
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                )
                save_tasks(tasks)
                st.success(
                    "✅ Response submit ho gaya! Admin ko notification update"
                    " dikhegi."
                )
                st.rerun()
              else:
                st.warning("Kripya Reason aur Action dono fields bharein!")
        else:
          st.success("Aapke saare pending inquiries solve ho chuke hain!")

      with tab_done:
        if len(completed_tasks) > 0:
          st.dataframe(
              completed_tasks[[
                  "Task_ID",
                  "Customer",
                  "Operator_Reason",
                  "Action_Taken",
                  "Reply_Date",
              ]],
              use_container_width=True,
          )
        else:
          st.write("Abhi tak koi response submit nahi hua hai.")

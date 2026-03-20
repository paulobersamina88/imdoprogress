
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="IMDO Project Progress Tracker", layout="wide")

DATA_DIR = Path("data")
PHOTOS_DIR = DATA_DIR / "photos"
PROJECTS_FILE = DATA_DIR / "projects_master.csv"
UPDATES_FILE = DATA_DIR / "progress_updates.csv"

DATA_DIR.mkdir(exist_ok=True)
PHOTOS_DIR.mkdir(exist_ok=True)

DEFAULT_PROJECT_COLUMNS = [
    "project_id", "project_title", "campus", "building", "project_type",
    "contractor", "abc", "contract_amount", "start_date", "target_completion",
    "status", "assigned_engineer", "remarks"
]

DEFAULT_UPDATE_COLUMNS = [
    "update_id", "project_id", "update_date", "planned_progress", "actual_progress",
    "slippage", "activity_done", "issue_observed", "action_needed", "next_activity",
    "inspector", "weather", "remarks", "photo_filename"
]

def init_csv(path: Path, columns: list[str]) -> None:
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)

init_csv(PROJECTS_FILE, DEFAULT_PROJECT_COLUMNS)
init_csv(UPDATES_FILE, DEFAULT_UPDATE_COLUMNS)

@st.cache_data
def load_projects():
    df = pd.read_csv(PROJECTS_FILE)
    if not df.empty:
        for col in ["abc", "contract_amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["start_date", "target_completion"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

@st.cache_data
def load_updates():
    df = pd.read_csv(UPDATES_FILE)
    if not df.empty:
        for col in ["planned_progress", "actual_progress", "slippage"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "update_date" in df.columns:
            df["update_date"] = pd.to_datetime(df["update_date"], errors="coerce")
    return df

def save_projects(df):
    df.to_csv(PROJECTS_FILE, index=False)
    st.cache_data.clear()

def save_updates(df):
    df.to_csv(UPDATES_FILE, index=False)
    st.cache_data.clear()

def rag_status(slippage):
    if pd.isna(slippage):
        return "Unknown"
    if slippage <= 0:
        return "Green"
    if slippage <= 10:
        return "Yellow"
    return "Red"

def latest_project_status(projects_df, updates_df):
    if projects_df.empty:
        return projects_df.copy()

    result = projects_df.copy()
    if updates_df.empty:
        result["latest_actual"] = 0.0
        result["latest_planned"] = 0.0
        result["latest_slippage"] = 0.0
        result["rag"] = "Unknown"
        return result

    updates_sorted = updates_df.sort_values("update_date")
    latest = updates_sorted.groupby("project_id", as_index=False).tail(1)[
        ["project_id", "planned_progress", "actual_progress", "slippage"]
    ].rename(columns={
        "planned_progress": "latest_planned",
        "actual_progress": "latest_actual",
        "slippage": "latest_slippage"
    })

    result = result.merge(latest, on="project_id", how="left")
    result["latest_planned"] = result["latest_planned"].fillna(0)
    result["latest_actual"] = result["latest_actual"].fillna(0)
    result["latest_slippage"] = result["latest_slippage"].fillna(0)
    result["rag"] = result["latest_slippage"].apply(rag_status)
    return result

def download_report_df(df, filename, label):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=csv, file_name=filename, mime="text/csv")

st.title("🏗️ IMDO Project Progress Tracker")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Project Registry", "Progress Encoder", "Project Detail", "Delays & Risks", "Reports"]
)

projects = load_projects()
updates = load_updates()
status_df = latest_project_status(projects, updates)

if page == "Dashboard":
    st.header("Executive Dashboard")

    total_projects = len(projects)
    ongoing = int(projects["status"].fillna("").str.contains("ongoing", case=False).sum()) if not projects.empty else 0
    completed = int(projects["status"].fillna("").str.contains("completed", case=False).sum()) if not projects.empty else 0
    delayed = int((status_df["rag"] == "Red").sum()) if not status_df.empty else 0
    total_value = float(projects["contract_amount"].fillna(0).sum()) if not projects.empty else 0
    avg_actual = float(status_df["latest_actual"].fillna(0).mean()) if not status_df.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Projects", total_projects)
    c2.metric("Ongoing", ongoing)
    c3.metric("Completed", completed)
    c4.metric("Critical Delay", delayed)
    c5.metric("Avg. Actual Progress", f"{avg_actual:.1f}%")

    st.metric("Total Contract Amount", f"PHP {total_value:,.2f}")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Projects by Campus")
        if not projects.empty and "campus" in projects.columns:
            campus_counts = projects["campus"].fillna("Unspecified").value_counts()
            fig, ax = plt.subplots()
            ax.bar(campus_counts.index.astype(str), campus_counts.values)
            ax.set_ylabel("Projects")
            ax.set_xlabel("Campus")
            ax.tick_params(axis="x", rotation=30)
            st.pyplot(fig)
        else:
            st.info("No campus data yet.")

    with col_b:
        st.subheader("RAG Status")
        if not status_df.empty:
            rag_counts = status_df["rag"].fillna("Unknown").value_counts()
            fig, ax = plt.subplots()
            ax.pie(rag_counts.values, labels=rag_counts.index, autopct="%1.0f%%")
            st.pyplot(fig)
        else:
            st.info("No progress data yet.")

    st.subheader("Latest Status Snapshot")
    display_cols = [
        "project_id", "project_title", "campus", "status",
        "latest_planned", "latest_actual", "latest_slippage", "rag"
    ]
    existing_cols = [c for c in display_cols if c in status_df.columns]
    st.dataframe(status_df[existing_cols], use_container_width=True)

elif page == "Project Registry":
    st.header("Project Registry")

    with st.expander("Add New Project", expanded=True):
        with st.form("add_project_form"):
            c1, c2, c3 = st.columns(3)
            project_id = c1.text_input("Project ID")
            project_title = c2.text_input("Project Title")
            campus = c3.selectbox("Campus", ["TUP Manila", "TUP Taguig", "TUP Clark", "Other"])

            c4, c5, c6 = st.columns(3)
            building = c4.text_input("Building")
            project_type = c5.selectbox("Project Type", ["Repair", "Renovation", "New Construction", "Retrofit", "Upgrade"])
            contractor = c6.text_input("Contractor")

            c7, c8, c9 = st.columns(3)
            abc = c7.number_input("ABC", min_value=0.0, step=1000.0, format="%.2f")
            contract_amount = c8.number_input("Contract Amount", min_value=0.0, step=1000.0, format="%.2f")
            assigned_engineer = c9.text_input("Assigned Engineer")

            c10, c11, c12 = st.columns(3)
            start_date = c10.date_input("Start Date", value=None)
            target_completion = c11.date_input("Target Completion", value=None)
            status = c12.selectbox("Status", ["Planned", "For Procurement", "Ongoing", "Completed", "On Hold"])

            remarks = st.text_area("Remarks")
            submitted = st.form_submit_button("Save Project")

            if submitted:
                if not project_id or not project_title:
                    st.error("Project ID and Project Title are required.")
                elif project_id in projects["project_id"].astype(str).tolist():
                    st.error("Project ID already exists.")
                else:
                    new_row = pd.DataFrame([{
                        "project_id": project_id,
                        "project_title": project_title,
                        "campus": campus,
                        "building": building,
                        "project_type": project_type,
                        "contractor": contractor,
                        "abc": abc,
                        "contract_amount": contract_amount,
                        "start_date": start_date,
                        "target_completion": target_completion,
                        "status": status,
                        "assigned_engineer": assigned_engineer,
                        "remarks": remarks,
                    }])
                    save_projects(pd.concat([projects, new_row], ignore_index=True))
                    st.success("Project saved.")
                    st.rerun()

    st.subheader("Current Projects")
    if not status_df.empty:
        st.dataframe(status_df, use_container_width=True)
        download_report_df(status_df, "projects_registry.csv", "Download Registry CSV")
    else:
        st.info("No projects yet.")

elif page == "Progress Encoder":
    st.header("Progress Encoder")

    if projects.empty:
        st.warning("Please add a project in Project Registry first.")
    else:
        with st.form("progress_form"):
            project_options = projects[["project_id", "project_title"]].copy()
            project_options["label"] = project_options["project_id"].astype(str) + " - " + project_options["project_title"].astype(str)
            selected_label = st.selectbox("Project", project_options["label"].tolist())
            selected_project_id = selected_label.split(" - ")[0]

            c1, c2, c3 = st.columns(3)
            update_date = c1.date_input("Update Date")
            planned_progress = c2.number_input("Planned Progress (%)", min_value=0.0, max_value=100.0, step=1.0)
            actual_progress = c3.number_input("Actual Progress (%)", min_value=0.0, max_value=100.0, step=1.0)
            slippage = planned_progress - actual_progress

            st.caption(f"Computed slippage: {slippage:.1f}%")

            c4, c5 = st.columns(2)
            inspector = c4.text_input("Inspector / IMDO Staff")
            weather = c5.selectbox("Weather", ["Sunny", "Cloudy", "Rainy", "Mixed", "Other"])

            activity_done = st.text_area("Activity Done")
            issue_observed = st.text_area("Issue Observed")
            action_needed = st.text_area("Action Needed")
            next_activity = st.text_area("Next Activity")
            remarks = st.text_area("Remarks")

            photo = st.file_uploader("Upload Site Photo", type=["jpg", "jpeg", "png"])
            submitted = st.form_submit_button("Save Update")

            if submitted:
                update_id = f"{selected_project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                photo_filename = ""

                if photo is not None:
                    project_photo_dir = PHOTOS_DIR / selected_project_id
                    project_photo_dir.mkdir(exist_ok=True)
                    photo_filename = f"{update_id}_{photo.name}"
                    with open(project_photo_dir / photo_filename, "wb") as f:
                        f.write(photo.getbuffer())

                new_row = pd.DataFrame([{
                    "update_id": update_id,
                    "project_id": selected_project_id,
                    "update_date": update_date,
                    "planned_progress": planned_progress,
                    "actual_progress": actual_progress,
                    "slippage": slippage,
                    "activity_done": activity_done,
                    "issue_observed": issue_observed,
                    "action_needed": action_needed,
                    "next_activity": next_activity,
                    "inspector": inspector,
                    "weather": weather,
                    "remarks": remarks,
                    "photo_filename": photo_filename,
                }])
                save_updates(pd.concat([updates, new_row], ignore_index=True))
                st.success("Progress update saved.")
                st.rerun()

    st.subheader("Recent Updates")
    if not updates.empty:
        recent = updates.sort_values("update_date", ascending=False).head(20)
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("No updates yet.")

elif page == "Project Detail":
    st.header("Project Detail")

    if projects.empty:
        st.warning("No projects available.")
    else:
        project_options = projects[["project_id", "project_title"]].copy()
        project_options["label"] = project_options["project_id"].astype(str) + " - " + project_options["project_title"].astype(str)
        selected_label = st.selectbox("Select Project", project_options["label"].tolist())
        selected_project_id = selected_label.split(" - ")[0]

        project_row = status_df[status_df["project_id"].astype(str) == selected_project_id].iloc[0]
        project_updates = updates[updates["project_id"].astype(str) == selected_project_id].sort_values("update_date")

        c1, c2, c3 = st.columns(3)
        c1.metric("Current Actual", f"{project_row.get('latest_actual', 0):.1f}%")
        c2.metric("Current Planned", f"{project_row.get('latest_planned', 0):.1f}%")
        c3.metric("Slippage", f"{project_row.get('latest_slippage', 0):.1f}%")

        st.subheader("Project Information")
        info_cols = ["project_id", "project_title", "campus", "building", "project_type", "contractor", "status", "assigned_engineer", "remarks"]
        info_df = pd.DataFrame(project_row[info_cols]).reset_index()
        info_df.columns = ["Field", "Value"]
        st.table(info_df)

        st.subheader("Planned vs Actual Progress")
        if not project_updates.empty:
            fig, ax = plt.subplots()
            ax.plot(project_updates["update_date"], project_updates["planned_progress"], marker="o", label="Planned")
            ax.plot(project_updates["update_date"], project_updates["actual_progress"], marker="o", label="Actual")
            ax.set_ylabel("Progress (%)")
            ax.set_xlabel("Update Date")
            ax.legend()
            ax.tick_params(axis="x", rotation=30)
            st.pyplot(fig)
        else:
            st.info("No updates for this project yet.")

        st.subheader("Timeline / Update Log")
        if not project_updates.empty:
            for _, row in project_updates.sort_values("update_date", ascending=False).iterrows():
                with st.expander(f"{pd.to_datetime(row['update_date']).date()} | Actual {row['actual_progress']}% | Planned {row['planned_progress']}%"):
                    st.write(f"**Activity Done:** {row['activity_done']}")
                    st.write(f"**Issue Observed:** {row['issue_observed']}")
                    st.write(f"**Action Needed:** {row['action_needed']}")
                    st.write(f"**Next Activity:** {row['next_activity']}")
                    st.write(f"**Inspector:** {row['inspector']}")
                    st.write(f"**Weather:** {row['weather']}")
                    st.write(f"**Remarks:** {row['remarks']}")
                    if row.get("photo_filename"):
                        photo_path = PHOTOS_DIR / selected_project_id / str(row["photo_filename"])
                        if photo_path.exists():
                            st.image(str(photo_path), caption=row["photo_filename"], use_container_width=True)
        else:
            st.info("No timeline entries yet.")

elif page == "Delays & Risks":
    st.header("Delays & Risks")

    if status_df.empty:
        st.info("No project data yet.")
    else:
        delayed_df = status_df[status_df["latest_slippage"] > 0].sort_values("latest_slippage", ascending=False)
        st.subheader("Projects with Slippage")
        if not delayed_df.empty:
            st.dataframe(delayed_df[[
                "project_id", "project_title", "campus", "status",
                "latest_planned", "latest_actual", "latest_slippage", "rag"
            ]], use_container_width=True)
            download_report_df(delayed_df, "delays_and_risks.csv", "Download Delay Report")
        else:
            st.success("No delayed projects based on current updates.")

elif page == "Reports":
    st.header("Reports")

    st.subheader("Download Data")
    download_report_df(projects, "projects_master.csv", "Download Projects Master")
    download_report_df(updates, "progress_updates.csv", "Download Progress Updates")

    st.subheader("Monthly Accomplishment Summary")
    if not updates.empty:
        summary = updates.copy()
        summary["month"] = pd.to_datetime(summary["update_date"]).dt.to_period("M").astype(str)
        monthly = summary.groupby(["month", "project_id"], as_index=False).agg({
            "planned_progress": "max",
            "actual_progress": "max",
            "slippage": "max"
        })
        st.dataframe(monthly, use_container_width=True)
        download_report_df(monthly, "monthly_accomplishment_summary.csv", "Download Monthly Summary")
    else:
        st.info("No update data yet.")

st.sidebar.markdown("---")
st.sidebar.caption("IMDO Streamlit starter app for project monitoring, documentation, and reporting.")

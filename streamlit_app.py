import pandas as pd
import streamlit as st

# Page layout
st.set_page_config(page_title="AZDOT Drainage Asset Search", layout="wide")


# Load data
@st.cache_data
def load_data():
  df = pd.read_csv("drainage_assets.csv")
  df.columns = df.columns.str.strip()
  return df


df = load_data()

# Ensure numeric types for mileposts
mp_from_col = "From MP/Offset"
if mp_from_col in df.columns:
  df[mp_from_col] = pd.to_numeric(df[mp_from_col], errors="coerce")

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Tool Mode",
    ["Filter & Search Tool", "Batch Asset ID Lookup & Sort"],
)

# ==========================================
# PAGE 1: ORIGINAL FILTER & SEARCH TOOL
# ==========================================
if page == "Filter & Search Tool":
  st.title("Arizona Highways Stormwater Drainage Assets Search")
  st.markdown(
      "Filter through 180,000+ drainage assets and access direct links to ADOT"
      " records and maps."
  )

  st.sidebar.header("Filter Assets")

  features = ["All"] + sorted(df["Feature"].dropna().unique().tolist())
  selected_feature = st.sidebar.selectbox("Feature", features)

  routes = ["All"] + sorted(df["Route"].dropna().unique().astype(str).tolist())
  selected_route = st.sidebar.selectbox("Route", routes)

  directions = [
      "All"
  ] + sorted(df["Direction"].dropna().unique().astype(str).tolist())
  selected_direction = st.sidebar.selectbox("Direction", directions)

  ramp_nums = [
      "All"
  ] + sorted(df["Ramp #"].dropna().unique().astype(str).tolist())
  selected_ramp_num = st.sidebar.selectbox("Ramp #", ramp_nums)

  ramp_ids = [
      "All"
  ] + sorted(df["Ramp ID"].dropna().unique().astype(str).tolist())
  selected_ramp_id = st.sidebar.selectbox("Ramp ID", ramp_ids)

  st.sidebar.markdown("### Milepost Range")
  min_mp = st.sidebar.number_input(
      "From MP / Offset (Min)", value=0.0, step=0.1
  )
  max_mp = st.sidebar.number_input(
      "To MP / Offset (Max)", value=500.0, step=0.1
  )

  filtered_df = df.copy()

  if selected_feature != "All":
    filtered_df = filtered_df[filtered_df["Feature"] == selected_feature]
  if selected_route != "All":
    filtered_df = filtered_df[
        filtered_df["Route"].astype(str) == selected_route
    ]
  if selected_direction != "All":
    filtered_df = filtered_df[
        filtered_df["Direction"].astype(str) == selected_direction
    ]
  if selected_ramp_num != "All":
    filtered_df = filtered_df[
        filtered_df["Ramp #"].astype(str) == selected_ramp_num
    ]
  if selected_ramp_id != "All":
    filtered_df = filtered_df[
        filtered_df["Ramp ID"].astype(str) == selected_ramp_id
    ]

  mp_to_col = "To MP/Offset"
  if mp_from_col in filtered_df.columns and mp_to_col in filtered_df.columns:
    filtered_df[mp_to_col] = pd.to_numeric(
        filtered_df[mp_to_col], errors="coerce"
    )
    filtered_df = filtered_df[
        (filtered_df[mp_from_col] >= min_mp)
        & (filtered_df[mp_to_col] <= max_mp)
    ]

  # Generate links
  filtered_df["FIS Link"] = filtered_df["Asset Id"].apply(
      lambda x: f"https://fis.dot.state.az/Inventory/Asset/ReadOnly?assetId={x}"
  )
  filtered_df["Google Street View"] = filtered_df.apply(
      lambda row: (
          f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row['Lat']},{row['Long']}"
          if pd.notnull(row["Lat"]) and pd.notnull(row["Long"])
          else None
      ),
      axis=1,
  )
  filtered_df["Google Map Pin"] = filtered_df.apply(
      lambda row: (
          f"https://www.google.com/maps/search/?api=1&query={row['Lat']},{row['Long']}"
          if pd.notnull(row["Lat"]) and pd.notnull(row["Long"])
          else None
      ),
      axis=1,
  )

  display_columns = {
      "Asset Id": "Asset ID",
      "Feature": "Feature",
      "Sub-Feature": "Sub Feature",
      "Route": "Route",
      "Ramp #": "Ramp #",
      "Ramp ID": "Ramp ID",
      "Org": "Org",
      "FIS Link": "FIS Link",
      "Google Street View": "Google Street View",
      "Google Map Pin": "Google Map Pin",
  }

  valid_cols = [
      col for col in display_columns.keys() if col in filtered_df.columns
  ]
  display_df = filtered_df[valid_cols].rename(columns=display_columns)

  st.write(f"**Matching Assets Found:** {len(display_df):,}")
  st.dataframe(
      display_df,
      use_container_width=True,
      column_config={
          "FIS Link": st.column_config.LinkColumn(
              "FIS Link", display_text="Open FIS"
          ),
          "Google Street View": st.column_config.LinkColumn(
              "Google Street View", display_text="Open Street View"
          ),
          "Google Map Pin": st.column_config.LinkColumn(
              "Google Map Pin", display_text="Open Map Pin"
          ),
      },
  )

  csv = filtered_df.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="Download Filtered Results as CSV",
      data=csv,
      file_name="filtered_drainage_assets.csv",
      mime="text/csv",
  )


# ==========================================
# PAGE 2: BATCH ASSET ID LOOKUP & ROUTE SORT
# ==========================================
elif page == "Batch Asset ID Lookup & Sort":
  st.title("Batch Asset ID Lookup & Route Sort")
  st.markdown(
      "Paste a list of Asset IDs below, click **Run Lookup**, and view a"
      " sequential table alongside an interactive map of all pins."
  )

  with st.form("batch_form"):
    raw_input_ids = st.text_area(
        "Paste Asset IDs (one per line, or separated by commas):",
        height=150,
        placeholder="2972761\n2973153\n2973154",
    )
    submit_button = st.form_submit_button(label="Run Lookup & Sort")

  if submit_button:
    if raw_input_ids.strip():
      import re

      user_ids = re.findall(r"\d+", raw_input_ids)
      user_ids = [int(i) for i in user_ids]

      batch_df = df[df["Asset Id"].isin(user_ids)].copy()

      if len(batch_df) > 0:
        # Sort by Route, Direction, and Milepost (Least to Greatest)
        sort_cols = [
            c for c in ["Route", "Direction", mp_from_col] if c in batch_df.columns
        ]
        batch_df = batch_df.sort_values(
            by=sort_cols, ascending=[True, True, True]
        )

        # Generate links
        batch_df["FIS Link"] = batch_df["Asset Id"].apply(
            lambda x: (
                f"https://fis.dot.state.az/Inventory/Asset/ReadOnly?assetId={x}"
            )
        )
        batch_df["Google Street View"] = batch_df.apply(
            lambda row: (
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row['Lat']},{row['Long']}"
                if pd.notnull(row["Lat"]) and pd.notnull(row["Long"])
                else None
            ),
            axis=1,
        )
        batch_df["Google Map Pin"] = batch_df.apply(
            lambda row: (
                f"https://www.google.com/maps/search/?api=1&query={row['Lat']},{row['Long']}"
                if pd.notnull(row["Lat"]) and pd.notnull(row["Long"])
                else None
            ),
            axis=1,
        )

        display_columns = {
            "Asset Id": "Asset ID",
            "Feature": "Feature",
            "Sub-Feature": "Sub Feature",
            "Route": "Route",
            "Direction": "Direction",
            "From MP/Offset": "From MP",
            "To MP/Offset": "To MP",
            "Org": "Org",
            "FIS Link": "FIS Link",
            "Google Street View": "Google Street View",
            "Google Map Pin": "Google Map Pin",
        }

        valid_cols = [
            col for col in display_columns.keys() if col in batch_df.columns
        ]
        display_batch_df = batch_df[valid_cols].rename(columns=display_columns)

        st.success(
            f"Successfully matched {len(display_batch_df)} of"
            f" {len(set(user_ids))} entered IDs."
        )

        # --- EMBEDDED INTERACTIVE MAP (Shows all pins at once) ---
        map_df = batch_df.dropna(subset=["Lat", "Long"]).rename(
            columns={"Lat": "latitude", "Long": "longitude"}
        )
        if len(map_df) > 0:
          st.subheader("Visual Map of Searched Assets")
          st.map(map_df, latitude="latitude", longitude="longitude", zoom=8)

        st.subheader("Sorted Asset List")
        st.dataframe(
            display_batch_df,
            use_container_width=True,
            column_config={
                "FIS Link": st.column_config.LinkColumn(
                    "FIS Link", display_text="Open FIS"
                ),
                "Google Street View": st.column_config.LinkColumn(
                    "Google Street View", display_text="Open Street View"
                ),
                "Google Map Pin": st.column_config.LinkColumn(
                    "Google Map Pin", display_text="Open Map Pin"
                ),
            },
        )

        batch_csv = batch_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Sorted Batch Results as CSV",
            data=batch_csv,
            file_name="sorted_batch_drainage_assets.csv",
            mime="text/csv",
        )
      else:
        st.warning(
            "None of the entered Asset IDs matched records in your database."
        )
    else:
      st.warning("Please paste at least one Asset ID.")

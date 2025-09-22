import streamlit as st
from pathlib import Path
from cli_src import create_the_CSV

st.set_page_config(page_title="CSV Creation", layout='wide')

st.markdown(
    """
    # About
    This is the creation of CSV page
    
    ## STEPS:
    1. select the path
    2. select run
    3. confirm order
    4. save in a location you can find again
    
    """
)
# output_type = st.selectbox("Output file type", ("csv","m3u"))
folder_path = st.text_input("Enter folder path:")


if folder_path and Path(folder_path).is_dir():
    st.success(f"Valid folder selected: {folder_path}")
    csv_config = {"in": Path(folder_path), "no_output":True}
    df = create_the_CSV.main(csv_config)
    # all_files = [f for f in Path(folder_path).rglob("*") if f.is_file()]
    st.subheader("Extracted Data")
    st.markdown(
    """
    use the icon above the table to downlaod the csv. you can edit it in the table by double clicking on an individual cell.
    keep in mind that this data is extracted from the audio files (uaully ID3 tags). This is what I will search for in plex.
    You can delete rows by selecting them in the left most column and using the trashbin in the top-right.
    """
    )
    st.write("Use the icon above the table to download the CSV. You can edit it inline.")
    st.write("Keep in mind that the data in the table is extracted from the audio files. This is ")
    edited_df = st.data_editor(df, num_rows="dynamic", hide_index=True)
    st.session_state.editable_df = edited_df
    
    
elif folder_path:
    st.error("That path is not a valid folder.")
    st.session_state.pop("edited_df",None)

if "editable_df" in st.session_state:
    col1, col2 = st.columns(2)
    col1.download_button(
        label="Download data as CSV",
        data = st.session_state.editable_df.to_csv(index=False).encode('utf-8'),
        file_name="plex_playlist.csv",
        mime='text/csv'
    )
    col2.download_button(
        label="Download data as m3u",
        data = create_the_CSV.get_m3u_str(st.session_state.editable_df).encode('utf-8'),
        file_name="plex_playlist.m3u",
        mime='text/plain'
    )
import time
import streamlit as st
import queue
import threading
from pathlib import Path

from dotenv import dotenv_values, set_key
import pandas as pd

import create_plex_playlists
import create_the_CSV


st.set_page_config(page_title="Plex Management", layout='wide')


st.markdown(
"""
# Plex Playlist creator!
This tool creates the playlists in a human readable format (so you can edit them) and also adds them to plex.
""")

with st.expander("Steps to follow when importing music into plex"):
    st.markdown(
    """
    1. Get your music and make sure it is in the format that you use everywhere. Place this in a working directory.
        > Example `<artist>/<album>/<track>`
        > This is not required, but will save you a TON of time later
    2. Use the `Playlist File Creation` area to make a playlist of your files
    3. Copy and paste the files from a working directory into your main music storage.
        > Rely on your OS to identify duplicates when you copy and paste
        > If you dont want to rely on your OS to find duplcates, if you are on a unix system, you can use `fdupes -r --order name . --delete`.
        >> Note that this is an interactive delete, it wont automatically do anything, but read the manual first!
    4. tell plex to rescan for new music
    5. use the `Plex Playlist` area to add the playlist to plex
    """
)

st.write("Select the tab below to get started!")
    
tab1, tab2, tab3 = st.tabs(["Plex Configuration","Playlist File Creation", "Plex Playlist"])

with st.container(border=True):
    st.markdown("Tool created by Joel. Message uscan on discord for any feedback.")

with tab1:
    env_path = create_plex_playlists.get_env_path()
    st.write(f"The .env file path is `{env_path}` in case you want to modify it outside of this web interface.")
    st.markdown("""If you need assistance getting your plex token please go [here](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)""")
    st.warning("Keep this data to yourself, you can delete files remotely with this information")

    if st.toggle("Show/Modify the contents of the file"):
        st.session_state.plex_valid = False
        plex_config = dotenv_values(env_path)
        # validate the data
        if "PLEX_TOKEN" not in plex_config:
            plex_config["PLEX_TOKEN"] = "SET THIS VALUE"
        
        if "PLEX_URL" not in plex_config:
            plex_config["PLEX_URL"] = "SET THIS VALUE"
        
        if "PLEX_PORT" not in plex_config:
            plex_config["PLEX_PORT"] = '32400 <- Confirm this is correct'
        

        editable_data = st.data_editor(plex_config)
        col1, col2, col3 = st.columns([1,1,4])

        if col1.button("test connection"):
            try:
                plex_server = create_plex_playlists.get_plex(
                    editable_data["PLEX_URL"], 
                    editable_data["PLEX_PORT"],
                    editable_data["PLEX_TOKEN"])
                st.session_state.plex_valid = True
            except Exception as e:
                print(f"{e}")
                st.toast(f"Could not make connection to Plex server. Error: {e}",duration='long')
                st.session_state.plex_valid = False
            

        if col2.button("Save Contents back to .env file", disabled=not(st.session_state.plex_valid)):
            for key,value in editable_data.items():
                set_key(env_path, key, value) # type: ignore

with tab2:
    st.markdown(
    """
    ## STEPS:
    1. Type in the path
    2. Hit enter
    3. Confirm the data (modify it if you want)
    4. Save the data in the type and location you want
    
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

with tab3:
    st.markdown(
    """
    ## STEPS:
    1. upload the playlist file (CSV/M3U)
    2. Find the tracks in plex
    3. edit the data in step 2 if not able to find them in plex
    4. create the playlist
    5. Enjoy! 
    
    """
    )
    file_upload = st.file_uploader("FilePath?", type=["csv","m3u"])

    if file_upload:
        if file_upload.type == "audio/x-mpegurl":
            df = create_the_CSV.parse_m3u_file(file_upload.getvalue().decode('utf-8'))
        else:
            df = pd.read_csv(file_upload)
        edited_df = st.data_editor(df, num_rows="dynamic", hide_index=True)

        col1, col2, col3 = st.columns([2,2,4])
        if col2.button("Update Music Library in Plex"):
            plex_server = create_plex_playlists.get_plex()
            library =create_plex_playlists.get_music_library(plex_server)
            library.update()
            # print(f"{plex_server.activities[0]=}")
            with st.spinner("Waiting for plex to finish updating", show_time=True):
                while len(plex_server.activities) > 0:
                    time.sleep(0.3)
            st.toast("Library is done updating!!", duration='long')
            

        if col1.button("Find Tracks in Plex"):
            progress_queue = queue.Queue(maxsize=1)
            current_item_queue = queue.Queue(maxsize=1)
            return_queue = queue.Queue(maxsize=1)
            progress_bar = st.progress(0)
            current_item_text = st.empty()
            plex_server = create_plex_playlists.get_plex()
            st.session_state.plex_server = plex_server
            library = create_plex_playlists.get_music_library(plex_server)
            t = threading.Thread(target=create_plex_playlists.find_all_tracks_from_df, args=(library, edited_df, progress_queue, current_item_queue, return_queue))
            t.start()
            while t.is_alive() or not progress_queue.empty():
                try:
                    (n, total) = progress_queue.get(timeout=0.1)
                    percent_done = float(n)/total
                    progress_bar.progress(percent_done,f"{percent_done*100.0:0.1f}% done")

                except queue.Empty:
                    pass
                try:
                    (artist, track, album) = current_item_queue.get(timeout=0.1)
                    current_item_text.text(f"finding Artist: {artist}, Track: {track}")
                except queue.Empty:
                    pass
                
            
            t.join()
            progress_bar.empty()
            current_item_text.empty()
            (playlist_tracks, tracks_not_found) = return_queue.get()
            st.session_state.playlist_tracks = playlist_tracks
            st.session_state.tracks_not_found = tracks_not_found

    else:
        st.session_state.pop("playlist_tracks",None)
        st.session_state.pop("tracks_not_found", None)

    if "playlist_tracks" in st.session_state:
        st.write("Results")
        (col1, col2) = st.columns(2)
        col1.write("Not Found Tracks")
        col1.write(st.session_state.tracks_not_found)
        col2.write("Found Tracks")
        col2.write(st.session_state.playlist_tracks)
        st.write("Note that only found tracks will be added. you can edit the data and the `Find Tracks in Plex` again.")

    if "playlist_tracks" in st.session_state and "plex_server" in st.session_state:
        playlist_name = st.text_input(label="Playlist Name")
        if playlist_name:
            (created,reason) = create_plex_playlists.create_playlist_from_found_tracks(
                st.session_state.plex_server, 
                playlist_name=playlist_name,
                track_list=st.session_state.playlist_tracks)
            if created:
                st.success("Playlist created!")
            else:
                st.error(f"Playlist not created because {reason}")
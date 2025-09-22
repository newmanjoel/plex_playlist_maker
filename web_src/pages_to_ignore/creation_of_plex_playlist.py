import queue
import threading
import streamlit as st
import pandas as pd
from cli_src import create_plex_playlists
from cli_src import create_the_CSV


st.markdown(
    """
    # About
    This is the creation of plex playlist page
    
    ## STEPS:
    1. upload the playlist file (CSV/M3U)
    2. Make sure its what you want
    2. Find the tracks in plex
    3. have a coffee
    4. enjoy music
    
    """
)
file_upload = st.file_uploader("FilePath?", type=["csv","m3u"])

if file_upload:
    # print(f"{file_upload=}")
    # print(f"{file_upload.__dict__}")
    if file_upload.type == "audio/x-mpegurl":
        df = create_the_CSV.parse_m3u_file(file_upload.getvalue().decode('utf-8'))
    else:
        df = pd.read_csv(file_upload)
    edited_df = st.data_editor(df, num_rows="dynamic", hide_index=True)

    if st.button("Find Tracks in Plex"):
        progress_queue = queue.Queue(maxsize=1)
        current_item_queue = queue.Queue(maxsize=1)
        return_queue = queue.Queue(maxsize=1)
        progress_bar = st.progress(0)
        # status_text =st.empty()
        current_item_text = st.empty()
        plex_server = create_plex_playlists.get_plex()
        st.session_state.plex_server = plex_server
        library = create_plex_playlists.get_music_library(plex_server)
        t = threading.Thread(target=create_plex_playlists.find_all_tracks_from_df, args=(library, edited_df, progress_queue, current_item_queue, return_queue))
        # create_plex_playlists.find_all_tracks_from_df(library, edited_df)
        t.start()
        while t.is_alive() or not progress_queue.empty():
            try:
                (n, total) = progress_queue.get(timeout=0.1)
                percent_done = float(n)/total
                progress_bar.progress(percent_done,f"{percent_done*100.0:0.1f}% done")
                # status_text.text(f"{percent_done*100.0:0.1f}% done")
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




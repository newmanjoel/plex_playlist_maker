
import argparse
import datetime
import os
from pathlib import Path
import sys
import plexapi
import plexapi.audio
import plexapi.base
import plexapi.library
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.library import LibrarySection
from plexapi.library import Library
import pandas as pd
from fuzzywuzzy import fuzz
import queue

from dotenv import dotenv_values




# Tracks parent is an album


def cli_inputs(inputs: list[str]) -> dict[str,any]: # type: ignore
    parser = argparse.ArgumentParser(description="a tool for creating a playlist in plex from a spotify playlist export")
    parser.add_argument("in",type=Path, help="path of the input CSV or M3U file")
    parser.add_argument("playlist_name", type=str, default=None, help="what you want the playlist to be called. Leave blank to use the name of the csv file as the playlist name")
    parser.add_argument('--out', type=argparse.FileType('w'), default=sys.stdout, help='where to write files that were not added to the playlist. Default: stdout')
    results = parser.parse_args(inputs)

    return results.__dict__

def get_env_path() -> str:
    # finding the local .env file
    module_directory = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(module_directory, ".env")
    return env_path

def get_plex(url:str|None = None, port:str|None = None, token:str|None = None, env_path:str=get_env_path()) -> PlexServer:
    if url is None or port is None or token is None:
        plex_config = dotenv_values(env_path)

        if url is None:
            url = plex_config.get("PLEX_URL", None)
            assert(url is not None)
        
        if port is None:
            port = plex_config.get("PLEX_PORT", None)
            assert(port is not None)
        
        if token is None:
            token = plex_config.get("PLEX_TOKEN", None)
            assert(token is not None)
    return PlexServer(f"{url}:{port}", token)

def get_music_library(plex:PlexServer|None = None):
    if plex is None:
        plex = get_plex()
    return plex.library.section("Music")


def get_artists(library:plexapi.library.MusicSection , artist:str) -> list[plexapi.audio.Artist]:
    search_results = library.search(f"{artist}", libtype="artist")
    return search_results

def get_tracks(library:plexapi.library.MusicSection , track:str) -> list[plexapi.audio.Track]:
    search_results = library.search(f"{track}", libtype="track")
    return search_results

def get_track_from_artist(library:plexapi.library.MusicSection , artist:str, track:str) -> plexapi.audio.Track|None:
    artist_results = get_artists(library, artist)
    for plex_artist in artist_results:
        all_plex_tracks = plex_artist.tracks()
        for plex_track in all_plex_tracks:
            ratio_score = fuzz.token_set_ratio(track, plex_track.title) # type: ignore
            if ratio_score == 100:
                return plex_track
    return None

def find_track(track_list:list[plexapi.audio.Track], search_track:str) -> plexapi.audio.Track|None:
    for track in track_list:
        track_score = fuzz.token_set_ratio(search_track, track.title)
        if track_score == 100 and not search_track:
            return track
    return None


def get_track_from_album(library:plexapi.library.MusicSection, search_album:str, search_artist:str, search_track:str) -> plexapi.audio.Track|None:
    plex_albums = library.search(search_album, libtype='album')
    for album in plex_albums:
        plex_artist_name = album.parentTitle
        # plex_artist_name = album.artist().title
        artist_score = fuzz.token_set_ratio(search_artist, plex_artist_name)
        if artist_score == 100:
            tracks = album.tracks()
            found_track = find_track(tracks, search_track)
            if found_track is None:
                continue
            return found_track
    return None

def get_track_from_track(library:plexapi.library.MusicSection, search_album:str, search_artist:str, search_track:str) -> plexapi.audio.Track|None:
    plex_tracks = get_tracks(library, search_track)
    for track in plex_tracks:
        #TODO: change the artist to grandparent name?
        # plex_artist_name = track.artist().title
        plex_artist_name = track.grandparentTitle
        plex_file_path = track.locations[0]
        artist_score = fuzz.token_set_ratio(search_artist, plex_artist_name)
        if artist_score == 100 or search_artist in plex_file_path:
            return track
    return None
        
def delete_all_added_tracks_between_times(library: plexapi.library.MusicSection, startpoint:datetime.datetime, endpoint:datetime.datetime):
    all_tracks = library.all(libtype='track')

    for track in all_tracks:
        addedDate = track.addedAt
        if addedDate > startpoint and addedDate < endpoint:
            print(f"deleting track `{track.title}` from location `{track.locations[0]}`")
            # track.delete()

def find_all_tracks_from_df(library: plexapi.library.MusicSection, search_data:pd.DataFrame, progress_queue:queue.Queue|None = None, current_item_queue:queue.Queue|None = None, return_queue:queue.Queue|None = None) -> tuple[list[plexapi.audio.Track], list[tuple[str,str,str]]]:
    playlist_tracks:list[plexapi.audio.Track] = []
    not_found_tracks:list[tuple[str,str,str]] = []

    # use lib.search(f"{artist}") and that will return an array of artists with the matching name.
    # if none found, returns an empty array

    is_spotify_csv = "Artist Name(s)" in search_data.columns


    total_rows = search_data.shape[0]
    for index, data_row in search_data.iterrows(): #[['Album Name',"Track Name", "Artist Name(s)"]]:
        
        if progress_queue is not None:
            try:
                progress_queue.put_nowait((index, total_rows))
            except queue.Full:
                pass # drop the update, its ok
        
        if is_spotify_csv:
            (album_name, track_name, artist_names) = data_row[['Album Name',"Track Name", "Artist Name(s)"]]
        else:
            (album_name, track_name, artist_names) = data_row[['Album',"Track", "Artist"]]

        if current_item_queue is not None:
            try:
                current_item_queue.put_nowait((artist_names, track_name, album_name))
            except queue.Full:
                pass # drop the update, its ok


        found_track = get_track_from_album(library, album_name, artist_names, track_name)

        if found_track is None:
            found_track = get_track_from_artist(library, artist_names, track_name)
        
        if found_track is None:
            found_track = get_track_from_track(library, album_name, artist_names, track_name)

        if found_track is not None:
            playlist_tracks.append(found_track)
        else:
            not_found_tracks.append(data_row) # type: ignore

    if return_queue is not None:
        try:
            return_queue.put_nowait((playlist_tracks, not_found_tracks))
        except queue.Full:
            pass # not really ok, but ehhhhhhh
    return (playlist_tracks, not_found_tracks)


def create_playlist_from_found_tracks(plex:PlexServer, playlist_name:str, track_list:list[plexapi.audio.Track]) -> tuple[bool, str]:


    all_playlists = plex.playlists(playlistType='audio')
    for playlist in all_playlists:
        if playlist.title == playlist_name: # type: ignore
            return (False, "playlist name already exists")
    print(f"{plex=}")
    print(f"{playlist_name=}")
    print(f"{track_list=}")
    new_playlist = Playlist.create(server=plex, title=playlist_name,section=plex.library.section("Music"), items=track_list)
    print(f"{new_playlist=}")
    print(f"{new_playlist.__dict__=}")
    return (True,playlist_name)


def main(config:dict):

    from_csv:Path = config.get("in",Path("test.csv"))
    if not from_csv.exists():
        raise FileNotFoundError()
    
    csv = pd.read_csv(from_csv)

    plex = get_plex()    
    lib = plex.library.section("Music")

    # #TODO: REMOVE THIS

    # delete_all_added_tracks_between_times(lib, datetime.datetime(2025, 9, 18), datetime.datetime.now())
    # return

    
    (playlist_tracks, not_found_tracks) = find_all_tracks_from_df(lib, csv)
    
    if len(not_found_tracks) != 0:
        not_found_df = pd.concat(not_found_tracks, axis=1) # type: ignore
        not_found_df = not_found_df.T

        print("all tracks that could not be found")
        print(not_found_df)
        output_method = config.get('out', sys.stdout)
        not_found_df.to_csv(output_method)

        if output_method is not sys.stdout:
            output_method.close() # type: ignore

            
    
    playlist_name = config.get("playlist_name", f"{from_csv.name} Playlist")
    new_playlist = Playlist.create(server=plex, title=playlist_name,section=plex.library.section("Music"), items=playlist_tracks)
    print(f"{new_playlist=}")
    print(f"{new_playlist.__dict__=}")
                


if __name__ == "__main__":
    # create_csv(Path("/home/joel/Downloads/Telegram Desktop/Renamed Music"), Path("files.txt"))
    # cli_config = cli_inputs([r"/home/joel/Desktop/spotify playlists/cole_and_megans_wedding_tunes.csv"])
    cli_config = cli_inputs(sys.argv[1:])

    main(cli_config)

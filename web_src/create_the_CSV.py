import logging
logger = logging.getLogger("plex_playlist_creator")
logger.info("create_the_csv file")
import argparse
from pathlib import Path
import re
import sys

logger.info("create_the_csv file loading")
import mutagen
import mutagen.id3
import pandas as pd
logger.info("create_the_csv modules loaded")

def cli_inputs(inputs: list[str]) -> dict[str,any]: # type: ignore
    parser = argparse.ArgumentParser(description="a tool for exporting embeded data from music files")
    parser.add_argument("in",type=Path, help="folder that the music files live in")
    parser.add_argument("--no-output", action="store_true", help="use this flag to not have any output")
    parser.add_argument("--output-as-m3u", action="store_true", help="write the output as m3u format")
    parser.add_argument('--out', type=argparse.FileType('w'), default=sys.stdout, help='where to write files that were not added to the playlist. Default: stdout')
    results = parser.parse_args(inputs)

    return results.__dict__

def get_m3u_str(data:pd.DataFrame) -> str:
    output = "#EXTM3U\r\n\r\n"

    for index, data_row in data.iterrows():
        (artist, album, track, track_len, file_path) = data_row[["Artist","Album", "Track", "Track Length (seconds)", "Filepath"]]
        output += f"#EXTINF:{track_len},{artist} - {track}\r\n{file_path}\r\n"
        output += "\r\n"
    return output


def main(config:dict) -> pd.DataFrame:
    working_folder:Path = config.get("in", Path("."))
    assert(working_folder.exists())
    all_files = [f for f in working_folder.rglob("*") if f.is_file()]
    all_music = []
    for file in all_files:
        try:
            temp_file = mutagen.File(file) # type: ignore
            all_music.append(temp_file)
        except Exception as e:
            print(f"Caught Except for {file}. Not adding. \n{e}")
            all_music.append(file)

    df = pd.DataFrame([], columns=["Artist","Album", "Track", "Track Length (seconds)", "Filepath"])
    for song in all_music:
        if issubclass(type(song), mutagen.FileType): # type: ignore
            tags = song.tags
            info = song.info
            df.loc[len(df)] = [tags.get("Artist", ["?"])[0], tags.get("Album", ["?"])[0], tags.get("Title",["?"])[0], f"{info.length:0.0f}", song.filename]
        elif issubclass(type(song), Path):
            df.loc[len(df)] = ["?","?","?","?", song.absolute()]
    
    if not config.get("no_output", False):
        print(f"{df}")
        output_method = config.get("out",sys.stdout)
        if config.get('output_as_m3u', False):
            output_method.write(get_m3u_str(df))
        else:
            df.to_csv(output_method, index=False)
            if output_method is not sys.stdout:
                output_method.close()
    return df

def parse_m3u_file(inputs:str) -> pd.DataFrame|None:
    if not inputs.startswith("#EXTM3U"):
        return None
    extinf_re = r"#EXTINF:(?P<length>.+?),(?P<artist>.+?) - (?P<track>.+?)\n(?P<filepath>.+?)\n"
    results = re.findall(extinf_re, inputs)
    df = pd.DataFrame(results, columns=["Track Length (seconds)", "Artist", "Track", "Filepath"])
    df["Album"] = "?"
    return df


    # for line in inputs.splitlines(keepends=False):
    #     if line.startswith("#EXTINF"):



if __name__ == "__main__":
    # config = cli_inputs([r'/home/joel/Downloads/Telegram Desktop/Expanded FIles', '--out', r'/home/joel/Desktop/plex_playlists/plex_playlist_maker/file_infos.csv'])
    # config = cli_inputs([r'/home/joel/Downloads/Telegram Desktop/Expanded FIles', '--output-as-m3u', '--out', r'/home/joel/Desktop/plex_playlists/plex_playlist_maker/file_infos.m3u'])
    m3u_text = Path(r'/home/joel/Desktop/plex_playlists/plex_playlist_maker/file_infos.m3u').read_text()
    parse_m3u_file(m3u_text)
    # config = cli_inputs(sys.argv[1:])
    # df = main(config)
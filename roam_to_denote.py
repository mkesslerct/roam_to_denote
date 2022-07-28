from datetime import datetime, timezone, timedelta
import shutil
import os
import pathlib
from pathlib import Path
import pandas as pd


# from https://www.peterbe.com/plog/fastest-python-function-to-slugify-a-string
import re
non_url_safe = ['"', '#', '$', '%', '&', '+',
                    ',', '/', ':', ';', '=', '?',
                    '@', '[', '\\', ']', '^', '`',
                    '{', '|', '}', '~', "'", "<", ">", "-"]
non_url_safe_regex = re.compile(
    r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
def slugify(text):
    text = non_url_safe_regex.sub('', text).strip()
    text = u'-'.join(re.split(r'\s+', text))
    return text

# https://zditect.com/code/python/how-to-set-file-modification-time-mtime-in-python.html#:~:text=How%20to%20set%20file%20modification%20time%20%28mtime%29%20in,%28atime%2C%20mtime%29%20os.utime%20%28filename%2C%20times%3D%20%28stat.st_atime%2C%20mtime.timestamp%20%28%29%29%29
def set_file_modification_time(file_path, mtime):
    """
    Set the modification time of a given file_path to the given mtime.
    mtime must be a datetime object.
    """
    stat = os.stat(file_path)
    atime = stat.st_atime
    os.utime(file_path, times=(atime, mtime.timestamp()))

FROM_NOTES_DIR = Path("../../slip-box/pages")
TO_NOTES_DIR = Path("../../slip-box/denotes")

def retrieve_title_filetags(file_path):
    with open(file_path, "r") as f:
        title = None
        filetags = None
        for l in f:
            # print(l)
            if match_title := re.match(r"#\+title: (.*)$", l):
                title = slugify(match_title.group(1))
            if match_filetags := re.match(r"#\+filetags: (.*)$", l): 
                filetags = re.sub(r":|,", " ",match_filetags.group(1)).strip()
                filetags = u"_".join(re.split(r"\s+", filetags))
                
        return title, filetags

def retrieve_denote_date(file_path):
    denote_date = datetime.fromtimestamp(
        file_path.stat().st_mtime, #tz=timezone.utc
    ).strftime("%Y%m%dT%H%M%S")

    return denote_date

def retrieve_org_roam_id(file_path):
    with open(file_path, "r") as f:
        or_id = None
        in_properties = False
        for l in f:
            if re.match(r"^:PROPERTIES:", l):
               in_properties = True 
            or_id_match = re.match(r":ID:\s+(.+)$", l)
            if (in_properties & (or_id_match is not None)):
                or_id = or_id_match.group(1).strip()
            if re.match(r"^:END:", l):
               in_properties = False
        
    return or_id
        
def orgroam_to_denote_filename(file_path):
    date = retrieve_denote_date(file_path)
    title, keywords = retrieve_title_filetags(file_path)
    denote_filename = f"{date}--{title}__{keywords}.org"

    return denote_filename
 
def correct_mtime(path):
    ids = pd.Series(name="denote_id", dtype="object")
    for roam_note in path.glob("*.org"):
        denote_id = retrieve_denote_date(roam_note)
        ids.loc[roam_note] = denote_id
    ids.sort_values(inplace=True)
    prev = ""
    for i in ids.index:
        if ids.loc[i] <= prev:
            prev_dt = datetime.strptime(prev, "%Y%m%dT%H%M%S")
            set_file_modification_time(i, prev_dt + timedelta(seconds=1))
            ids.loc[i] = retrieve_denote_date(i)
        prev = ids.loc[i]

    return None

def build_org_roam_ids(path):
    # with open("org_roam_ids.csv", "w") as csv_file: 
    notes = dict()
    denote_ids = dict()
        # csv_file.write("path,id\n")
    for roam_note in path.glob("*.org"):
        or_id = retrieve_org_roam_id(roam_note)
        notes[or_id] = roam_note
        denote_id = retrieve_denote_date(roam_note)
        if denote_id in denote_ids.values():
            pass
            print(f"denote_id already exists {denote_id}. Current note: {roam_note.name}") 

            raise Exception(f"denote_id already exists {denote_id}. Current note: {roam_note.name}") 
        else:
            denote_ids[or_id] = denote_id
        # csv_file.write(f"{roam_note},{or_id}\n")

    return notes

def orgroam_to_denote(file_path, notes_dict):
    links_re = re.compile(r"\[\[id:(.*?)\]\[(.*?)\]\]")
    denote_path = TO_NOTES_DIR / orgroam_to_denote_filename(file_path)
    with open(file_path, "r") as orgroam_file:
        with open(denote_path, "w") as denote_file:
            in_properties = False
            for l in orgroam_file:
                shift = 0
                if re.match(r"^:PROPERTIES:", l):
                    in_properties = True 
                if re.match(r"^:END:", l):
                    in_properties = False
                    continue
                if in_properties:
                    continue
                for occurrence in links_re.finditer(l):
                    id = occurrence.group(1)
                    description = occurrence.group(2)
                    if not id in notes_dict:
                        raise Exception(f"file: {file_path.name}, inexistent id in link: {id} ")

                    denote_link =  f"denote:{retrieve_denote_date(notes_dict[id])}"
                    l = l[:(shift + occurrence.start(1) - 3)] + denote_link + l[shift + occurrence.end(1):]
                    shift = shift + len(denote_link) - (occurrence.end(1) - occurrence.start(1) + 3)
                denote_file.write(l)
                
    print(f"Org-roam note {file_path.name} converted to denote")
    

if __name__ == "__main__":    
    correct_mtime(FROM_NOTES_DIR)
    notes_dict = build_org_roam_ids(FROM_NOTES_DIR)
    for roam_note in FROM_NOTES_DIR.glob("*.org"):
        orgroam_to_denote(roam_note, notes_dict)










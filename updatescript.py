#!/usr/bin/env python3

"""A simple script to update UT4 hubs
Options:
(no options) : if PORT is not taken (hub isn't running) do all updates
-f           : run all updates, even if the hub is up
-r           : only update rulesets
-i           : only update ini's
-p           : only update paks

you may use any of these in combination with each other to produce the desired result"""

import os
import sys
import time 
import hashlib                  # md5sum
import re                       # parse references
import urllib.request           # download
import tempfile                 # ini rewriting
import shutil
import socket                   # check if server is running


__author__ = "MII#0255"
__credits__ = ["MII#0255", "skandalouz#1109", "Scoob#7073"]
__license__ = "MIT"
__version__ = "1.0.2"
__maintainer__ = "MII#0255"


#TODO THESE MUST BE CHANGED TO THE SUITABLE VALUES
PRIVCODE = "abcdefg0123456789"
SERVER_TOKEN = "abcdefg0123456789"
ALLOWED_RULES = "1,2,3,4,5"
HIDE_DEFAULTS = True
REFERENCE_FILENAME = 'references.txt'
PORT = 7777

PURGE_OLD = True # WARNING: set to false if you do not want unlisted paks deleted

HOME_PATH = os.path.split(os.path.realpath(__file__))[0]
PAK_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Content/Paks/")
INI_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Saved/Config/LinuxServer/Game.ini")
RULESET_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Saved/Config/Rulesets/rulesets.json")


def main(args):
    """runs the update, based on validation and user input"""

    output = validate()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1',PORT))

    if result != 0 and '-f' not in args:
        print('server appears to be running, use the argument -f if you would like to ignore this')
        return

    if not args or args == ['-f']: # update everything if theres no arguments or only -f
        print('No arguments specified, running full update')
        args = args + ['-r', '-i', '-p']

    references = download_references() # always get latest references

    if '-p' in args:
        if output[0]:
            download_new_paks(references)

        else:
            # invalid pak directory path error message
            print('please make sure that PAK_PATH points to a valid directory')

    if '-i' in args:
        if output[1]:
            overwrite_game_ini(references)

        else:
            # invalid ini path error message
            print('please make sure that INI_PATH points to your game ini')

    if '-r' in args: # update rulesets
        if not output[2]:
            print('Saving ruleset under new file:', RULESET_PATH)

        update_rulesets()




def validate():
    """checks file paths and makes sure the program is able to run"""
    pak_check = os.path.exists(PAK_PATH)
    ini_check = os.path.isfile(INI_PATH)
    rules_check = os.path.isfile(RULESET_PATH)

    return pak_check, ini_check, rules_check




def update_rulesets():
    """ a new ruleset file based on the info given above"""
    print('=============')
    print('Downloading ruleset')
    if HIDE_DEFAULTS:
        url_string = "http://utcc.unrealpugs.com/rulesets/download?privateCode={}&hideDefaults&rulesets={}"
    else:
        url_string = "http://utcc.unrealpugs.com/rulesets/download?privateCode={}&rulesets={}"
    urllib.request.urlretrieve(url_string.format(PRIVCODE, ALLOWED_RULES), RULESET_PATH)
    print('Ruleset downloaded to', RULESET_PATH)



def download_references():
    """downloads the latest ini configuration to "list.txt" and extracts its contents
        NOTE: this will download to cwd"""
    print('=============')
    print('Downloading references')
    path = os.path.join(HOME_PATH, REFERENCE_FILENAME)
    url_string = "https://utcc.unrealpugs.com/hub/{}/supersecretreferencesurl"
    urllib.request.urlretrieve(url_string.format(SERVER_TOKEN), path)

    with open('references.txt', 'r') as reference_file:
        print('References saved to', path)
        return reference_file.readlines()
    

def find_paks():
    """returns a dictionary of name:(path, checksum) reading the current pak files"""
    print('=============')
    print('Checking paks')
    file_list = [x for x in os.listdir(os.path.join(HOME_PATH, PAK_PATH)) if x.endswith('.pak')]
    file_list.remove('UnrealTournament-LinuxServer.pak') # don't mess with the main pak
    info = {}

    for file_name in file_list:
        file_path = os.path.join(PAK_PATH, file_name)
        with open(file_path, 'rb') as pakfile:
            md5 = hashlib.md5(pakfile.read()).hexdigest()

        print('---{} : {}'.format(file_name, md5))
        info.update({file_name:(file_path, md5)})

    print('All paks downloaded')
    return info

    
def download_new_paks(references):
    """given a list of references, cross-references with paks for matches 
        and then does the following things:
        ignore any matches
        if an item does not exist in the first list, but does in the second: download it
        for the reverse: if PURGE_OLD is set to true, delete the pak"""
    print('=============')
    new_paks = extract_info(references)
    current_paks = find_paks()

    to_download = []
    redundant = []
    downloaded = []

    for line in new_paks:
        name, ptc, url, md5 = line
        print(name)
        if name in current_paks and current_paks[name][1] == md5:
            print('---OK')
            del(current_paks[name])
            continue

        else:
            if name in current_paks:
                print('---version mismatch, deleting old')
                os.remove(current_paks[name][0])
                del(current_paks[name])

            print('---downloading')
            full_url = ptc+'://'+url
            destination = os.path.join(PAK_PATH, name)
            urllib.request.urlretrieve(full_url, destination)

            downloaded.append(name)


    print('The following has been downloaded:\n---'+ '\n---'.join(downloaded))
    if current_paks and PURGE_OLD: # remove old paks
        print('cross reference completed, deleting old paks')
        for redundant_pak_name, items in current_paks.items():
            print('---deleting', redundant_pak_name)
            os.remove(items[0])
            
        



def extract_info(reference_list):
    """given a list of references, extract all the information given into a more digestable form"""
    print('=============')
    print('Extracting reference information')
    return_list = []

    for reference in reference_list:
        reference_extract = re.findall(r'"([A-Za-z0-9_\./\\-]*)"', reference)
        reference_extract[0] = reference_extract[0]+'.pak'
        return_list.append(reference_extract)

    print('References extracted\n', '\n'.join([str(x) for x in return_list]))
    return return_list




def overwrite_game_ini(references):
    """given a list of references, overwrites the current references in game.ini"""
    print('=============')
    print('Rewriting game ini references')

    #Create temp file
    fh, abs_path = tempfile.mkstemp()
    with os.fdopen(fh,'w') as new_file:
        with open(INI_PATH) as old_file:
            for line in old_file:
                if not line.startswith("RedirectReferences=("):
                    new_file.write(line)

        for reference in references:
            new_file.write(reference)
        #Remove original file
        os.remove(INI_PATH)
        #Move new file
        shutil.move(abs_path, INI_PATH)


main(sys.argv[1:])

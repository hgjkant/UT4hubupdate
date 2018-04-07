import os
import sys
import time 
import hashlib                  # md5sum
import re                       # parse references
import urllib.request           # download
import tempfile                 # ini rewriting
import shutil


HOME_PATH = os.path.split(os.path.realpath(__file__))[0]
PAK_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Content/Paks/")
INI_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Saved/Config/LinuxServer/Game.ini")
RULESET_PATH = os.path.join(HOME_PATH, "LinuxServer/UnrealTournament/Saved/Config/Rulesets/rulesets.json")

PRIVCODE = "28pT34hJdIppodtKd97K9MwNqn0AjBdt"
SERVER_TOKEN = "QIKzedUbeVquGjofcyjQ7VQiO7sB2TDZ"
ALLOWED_RULES = "4,5,6,7,8,9,10,11,12,13,16,17,18,20,21,52,43,22,23,24,26,27,28,61,41,32,31,29,47"
HIDE_DEFAULTS = True
REFERENCE_FILENAME = 'references.txt'

PURGE_OLD = True # WARNING: set to false if you do not want unlisted paks deleted


def main(args):
    '''runs the update, based on validation and user input'''

    output = validate()
    references = download_references() # always get latest references

    if not args: # update everything if theres no arguments
        print('No arguments specified, running full update')
        args = args + ['-r', '-i', '-p']

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
        if output[2]:
            update_rulesets()

        else:
            # invalid ruleset path error message
            print('please make sure that RULESET_PATH points to a valid ruleset json')




def validate():
    '''checks file paths and makes sure the program is able to run'''
    pak_check = os.path.exists(PAK_PATH)
    ini_check = os.path.isfile(INI_PATH)
    rules_check = os.path.isfile(RULESET_PATH)

    return pak_check, ini_check, rules_check




def update_rulesets():
    ''' a new ruleset file based on the info given above'''
    print('=============')
    print('Downloading ruleset')
    if HIDE_DEFAULTS:
        url_string = "http://utcc.unrealpugs.com/rulesets/download?privateCode={}&hideDefaults&rulesets={}"
    else:
        url_string = "http://utcc.unrealpugs.com/rulesets/download?privateCode={}&rulesets={}"
    urllib.request.urlretrieve(url_string.format(PRIVCODE, ALLOWED_RULES), RULESET_PATH)
    print('Ruleset downloaded to', RULESET_PATH)



def download_references():
    '''downloads the latest ini configuration to "list.txt" and extracts its contents
        NOTE: this will download to cwd'''
    print('=============')
    print('Downloading references')
    path = os.path.join(HOME_PATH, REFERENCE_FILENAME)
    url_string = "https://utcc.unrealpugs.com/hub/{}/supersecretreferencesurl"
    urllib.request.urlretrieve(url_string.format(SERVER_TOKEN), path)

    with open('references.txt', 'r') as reference_file:
        print('References saved to', path)
        return reference_file.readlines()
    

def find_paks():
    '''returns a dictionary of name:(path, checksum) reading the current pak files'''
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
    '''given a list of references, cross-references with paks for matches 
        and then does the following things:
        ignore any matches
        if an item does not exist in the first list, but does in the second: download it
        for the reverse: if PURGE_OLD is set to true, delete the pak'''
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
    '''given a list of references, extract all the information given into a more digestable form'''
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
    '''given a list of references, overwrites the current references in game.ini'''
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

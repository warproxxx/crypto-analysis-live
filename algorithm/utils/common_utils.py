from io import BytesIO
import os
import numpy as np

def get_root_dir():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def merge_csvs(files, ignore_name=None):
    '''
    Appends csvs and returns

    Parameters:
    ___________

    files (List):
    List of files to append

    Returns:
    ________
    combined (BytesIO):
    BytesIO of the files. Returns None if there is no file
    '''
    combined = BytesIO()
    first = 1

    if ignore_name != None:
        ignored_files = [file for file in files if ignore_name not in file] 
    else:
        ignored_files = files

    if len(ignored_files) >= 1:
        for file in ignored_files:

            with open(file, "rb") as f:
                if (first != 1):
                    next(f)                
                else:
                    first = 0
                
                combined.write(f.read())

        combined.seek(0)        
        return combined
    else:
        return None

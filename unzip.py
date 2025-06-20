import gzip
import shutil
import os
def unzip(filename):
    with gzip.open(filename, 'rb') as f_in:
        with open(filename[:-4], 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(filename)

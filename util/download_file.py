import os, sys


def _download_file(filename, url):
    """
    Helper function for download_file().
    Not meant to be accessed directly, but it can be :)
    """
    try:
        os.system(f"curl -Lk -o {filename} {url} --create-dirs")
        return("*** downloaded", filename)
    except:
        return("cannot access URL for", filename)

    
def download_file(filename, url, overwrite=False):
    """
    Uses a system call to curl to download a file, specified by filename, from the specified url.
    By default, the file will not be downloaded if it exists. Use overwrite parameter to overide.
    """
    if (False == overwrite) and os.path.exists(filename):
        return(f"*** {filename} already exists")
    else:
        return _download_file(filename, url)

    
if '__main__' ==  __name__:
    try:
        if 3 == len(sys.argv): # by defaut files are not overwritten
           print(download_file(sys.argv[1], sys.argv[2]))
           
        elif 4 == len(sys.argv):  # checking for the overwrite parameter
            print(download_file(sys.argv[1], sys.argv[2], sys.argv[3]))
            
        else:
            print("wrong number of arguments for", __file__)

    except:
        print("ERROR executing", __file__)
        print(sys.exc_info()[0])

import os, sys

def download_file(filename, url):
    try:
        os.system(f"curl -Lk -o {filename} {url}")
        return("*** downloaded", filename)
    except:
        return("cannot access URL for", filename)
    
def main(filename, url, overwrite=False):
    if (False == overwrite) and os.path.exists(filename):
        return(f"*** {filename} already exists")
    else:
        return download_file(filename, url)

if '__main__' ==  __name__:
    try:
        if 3 == len(sys.argv): # by defaut files are not overwritten
           print( main(sys.argv[1], sys.argv[2]))
        elif 4 == len(sys.argv): # checking for the overwrite parameter
            print(main(sys.argv[1], sys.argv[2], sys.argv[3]))
        else:
            print("wrong number of arguments for", __file__)

    except:
        print("error executing", __file__)

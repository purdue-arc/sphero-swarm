import time
import os # for creating directory
import shutil # for removing directory

try:
    if __name__ == "__main__":
        try:
            os.mkdir(os.path.join(os.getcwd(), "algorithm"))
        except FileExistsError:
            pass
        fileNum = 0
        while True:
            fileName = "algorithm/Commands"+str(fileNum)+".txt"
            with open(fileName, "w") as file:
                file.write("Commands") # needs to be filed with actual commands though
                fileNum += 1
            time.sleep(1)
            
except KeyboardInterrupt:
    shutil.rmtree(os.path.join(os.getcwd(), "algorithm"))

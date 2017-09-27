import os

with open("meta.yaml", 'r') as fp:
    active = False
    for line in fp:
        line = line.strip()
        if line == "run:":
            active = True
        elif active == True:
            if line.startswith("-"):
                package = line[2:]
                if package != "python":
                    print("Install package:", package)
                    os.system("conda install -y "+package)
            else:
                active = False
os.system("pip install pyqt5")
os.system("pip install -e . --no-dependencies")

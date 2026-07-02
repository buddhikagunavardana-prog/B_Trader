import platform
import sys


def show_system_info():
    print(f"Python : {sys.version.split()[0]}")
    print(f"OS     : {platform.system()} {platform.release()}")
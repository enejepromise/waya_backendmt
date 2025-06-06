import os
import multiprocessing


cpu_count = multiprocessing.cpu_count()

print(f"Total CPU Count  -- {cpu_count}")



# Timeout setting
timeout = 60 * 10  


bind = f"0.0.0.0:3000"
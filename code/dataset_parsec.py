import os
import sys
import subprocess
import csv
from collections import defaultdict

WORKLOADS = ["blackscholes", "bodytrack", "canneal", "facesim", "ferret", "fluidanimate", "streamcluster", "swaptions", "vips", "x264"]
INPUT_SIZE = ["simsmall", "simmedium", "simlarge"]
THREADS = [1,2,4,8,16,32]
NUM_RUNS = 5
COLUMNS = ["IPC", "branch-instructions", "branch-misses", "branch-miss-rate", "cache-misses", "cache-miss-rate", "cache-references", "cycles", "instructions", "cpu-clock", "page-faults", "L1-dcache-loads", "L1-icache-load-misses", "LLC-load-misses", "run_time", "thread", "size", "workload", "speedup"]

def parse_run_time(output):
    for line in iter(output, ""):
        line = line.decode("utf-8")
        if "real" in line:
            values = line.strip().split("\t")
            real_value = values[1]
            minutes, sec = real_value.split("m")
            seconds, _ = sec.split("s")
            real_time = int(minutes) * 60 + float(seconds)
            return real_time

def parse_perf_output_file(output_path, data):
    with open(output_path, "r") as fp:
        content = fp.readlines()
    content = content[2:]
    for line in content:
        values = line.split(",")
        key = values[2]
        value = values[0]
        if key in data:
            data[key] += float(value)
        else:
            data[key] = float(value)
        
        if key == "instructions":
            new_key = "IPC"
            value = values[5]
            if new_key in data:
                data[new_key] += float(value)
            else:
                data[new_key] = float(value)
        if key == "branch-misses":
            new_key = "branch-miss-rate"
            value = values[5]
            if new_key in data:
                data[new_key] += float(value)
            else:
                data[new_key] = float(value)
        if key == "cache-misses":
            new_key = "cache-miss-rate"
            value = values[5]
            if new_key in data:
                data[new_key] += float(value)
            else:
                data[new_key] = float(value)

def build_workload(workload):
    proc = subprocess.Popen("./parsecmgmt -a build -p {}".format(workload), shell=True, stdout=subprocess.PIPE)
    proc.wait()

def run_workload(workload):
    for input_size in INPUT_SIZE:
        single_thread_time = 0
        for thread in THREADS:
            data = dict()
            for run in range(NUM_RUNS):
                print("Workload: {} Problem size: {} Thread: {} Run: {}".format(workload, input_size, thread, run))
                proc = subprocess.Popen("perf stat -o output.txt --field-separator=, -e branch-instructions,branch-misses,cache-misses,cache-references,cycles,instructions,cpu-clock,page-faults,L1-dcache-loads,L1-icache-load-misses,LLC-load-misses -- ./parsecmgmt -a run -p {} -n {} -i {}".format(workload, thread, input_size), shell=True, stdout=subprocess.PIPE)
                proc.wait()
                run_time = parse_run_time(proc.stdout.readline)
                parse_perf_output_file("output.txt", data)
                if "run_time" in data:
                    data["run_time"] += run_time
                else:
                    data["run_time"] = run_time
                print("Workload: {} Problem size: {} Thread: {} Run: {} -- DONE".format(workload, input_size, thread, run))
            for key in data.keys():
                data[key] = data[key] / NUM_RUNS
            if thread == 1:
                single_thread_time = data["run_time"]
            data["thread"] = thread
            data["size"] = input_size
            data["workload"] = workload
            data["speedup"] = single_thread_time / data["run_time"]
            with open("results.csv", "a") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=COLUMNS)
                writer.writerow(data)             

def uninstall_workload(workload):
    proc = subprocess.Popen("./parsecmgmt -a fulluninstall -p {}".format(workload), shell=True, stdout=subprocess.PIPE)
    proc.wait()

def main():
    with open("results.csv", "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COLUMNS)
        writer.writeheader()

    for workload in WORKLOADS:
        build_workload(workload)
        run_workload(workload)
        uninstall_workload(workload)

if __name__ == "__main__":
    main()
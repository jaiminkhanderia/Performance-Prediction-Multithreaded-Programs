# Steps to create the dataset:

# Download Splash 3.0 dataset
# Follow steps - https://github.com/SakalisC/Splash-3
# Run from the folder Splash3/codes/

# Importing modules
import subprocess, sys, os, csv

DATASET_FILENAME = "dataset_splash.csv"

PROBLEM_SIZES = {"radixsort": {"small": 4194304, "medium": 16777216, "large": 67108864}, 
                "lu_contig": {"small": 512, "medium": 1024, "large": 2048},
                "lu_noncontig": {"small": 512, "medium": 1024, "large": 2048}, 
                "fft": {"small": 20, "medium": 22, "large": 24},
                "ocean_contig": {"small": 514, "medium": 1026, "large": 2050},
                "ocean_noncontig": {"small": 514, "medium": 1026, "large": 2050}}

HEADERS = ['name', 'threads', 'size', 'branch-misses', 'branch-miss-rate', 'cache-references', 'cpu-clock', 'L1-icache-load-misses', 'cache-misses', 'cache-miss-rate', 'instructions', 'ipc', 'cycles', 'L1-dcache-loads', 'LLC-load-misses', 'branch-instructions', 'page-faults', 'real-time', 'single-thread-time', 'speedup']


def readfile(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
    
    return lines


def parse_real_time(cmd_output):
    for line in cmd_output:
        line = line.decode("utf-8")
        if "real" in line:
            values = line.strip().split("\t")
            real_value = values[1]
            minutes, sec = real_value.split("m")
            seconds, _ = sec.split("s")
            real_time = int(minutes) * 60 + float(seconds)
            return real_time


def parse_metrics_from_perf(metrics, lines):
    for currentline in lines[2:]:
        values = currentline.split(",")
        event_value = float(values[0])
        event_name = values[2].replace(":u", "")
        metrics[event_name] += event_value
        if(event_name.startswith('instructions')):
            metrics['ipc'] += float(values[5])
        elif(event_name.startswith('cache-misses')):
            metrics['cache-miss-rate'] += float(values[5])
        elif(event_name.startswith('branch-misses')):
            metrics['branch-miss-rate'] = float(values[5])
    
    return metrics
    

def get_data_for_module(module_name, command): 
    threads = [1, 2, 4, 8, 16, 32]
    with open(DATASET_FILENAME, "a") as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=HEADERS)

        for size in PROBLEM_SIZES[module_name]:
            single_thread_time = 0
            for thread in threads:
                metrics = {'branch-misses': 0, 'cache-references': 0, 'cpu-clock': 0, 'L1-icache-load-misses': 0, 'cache-misses': 0, 'instructions': 0, 'cycles': 0, 'L1-dcache-loads': 0, 'LLC-load-misses': 0, 'branch-instructions': 0, 'page-faults': 0, 'real-time': 0, 'ipc': 0, 'cache-miss-rate': 0, 'branch-miss-rate': 0}
                for _ in range(5):
                    command = command.replace("{threads}", str(thread)).replace("{problemsize}", str(PROBLEM_SIZES[module_name][size]))
                    cmd = subprocess.Popen("( time perf stat -o output.txt --field-separator=, -e branch-instructions,branch-misses,cache-misses,cache-references,cycles,instructions,cpu-clock,page-faults,L1-dcache-loads,L1-icache-load-misses,LLC-load-misses %s ) &> out" % command, shell=True, stdout=subprocess.PIPE)
                    cmd.wait()

                    cmdlines = readfile("out")
                    real_time_seconds = parse_real_time(cmdlines)
                    metrics['real-time'] += real_time_seconds

                    if(thread == 1):
                        single_thread_time += real_time_seconds

                    lines = readfile("output.txt")
                    metrics = parse_metrics_from_perf(metrics, lines)
        
                for metric in metrics:
                    metrics[metric] = metrics[metric] / 5

                metrics['single-thread-time'] = single_thread_time / 5
                metrics['speedup'] = metrics['single-thread-time']   / metrics['real-time']
                metrics.update({'name': module_name, 'threads': thread, 'size': str(PROBLEM_SIZES[module_name][size])})

                writer.writerow(metrics)
                print({'name': module_name, 'threads': thread, 'size': str(PROBLEM_SIZES[module_name][size])})


if __name__ == "__main__":
    module_to_cmd = {"radixsort": "kernels/radix/./RADIX -p{threads} -n{problemsize}",
                    "lu_contig": "kernels/lu/contiguous_blocks/./LU -p{threads} -n{problemsize}",
                    "lu_noncontig": "kernels/lu/non_contiguous_blocks/./LU -p{threads} -n{problemsize}",
                    "fft": "kernels/fft/./FFT -p{threads} -m{problemsize}",
                    "ocean_contig": "apps/ocean/contiguous_partitions/./OCEAN -p{threads} -n{problemsize}",
                    "ocean_noncontig": "apps/ocean/non_contiguous_partitions/./OCEAN -p{threads} -n{problemsize}"}

    with open(DATASET_FILENAME, "w") as f:
        writer = csv.DictWriter(f, delimiter=',', fieldnames=HEADERS)
        writer.writeheader()
    
    for module in module_to_cmd:
        print(module)
        get_data_for_module(module, module_to_cmd[module])

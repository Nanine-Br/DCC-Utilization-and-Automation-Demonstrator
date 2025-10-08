import threading
import multiprocessing
import subprocess
import sys

class ProcessManager:
    def __init__(self):
        self.threads = []  # List for Threads
        self.processes = []  # List for Sub- and multi-processes

    def add_thread(self, thread):
        """Adds a thread to the list."""
        self.threads.append(thread)

    def start_thread(self, target, name=None, daemon=True, args=()):
        """Starts a new thread and saves it in the list."""
        thread = threading.Thread(target=target, name=name, daemon=daemon, args=args)
        thread.start()
        self.threads.append(thread)
        return thread

    def start_multiprocess(self, target, name, args=()):
        """Starts a new multiprocess and saves it in the list."""
        multiprocessing.set_start_method("spawn", force=True)
        process = multiprocessing.Process(target=target, name=name, args=args)
        process.start()
        self.processes.append(process)
        return process
    
    def start_subprocess(self, command):
        """Starts a new subprocess and saves it in the list."""
        python_executable = sys.executable  # Path to the currently running Python interpreter (i.e., your .venv)
        process = subprocess.Popen(args = [python_executable, command], stdin=subprocess.PIPE, text=True)
        self.processes.append(process)
        return process

    def list_active_threads(self):
        """Displays an overview of all running threads."""
        print("\nAktive Threads:")
        for thread in self.threads:
            if thread.is_alive():
                print(f"- {thread.name} with {thread.native_id} in process.")
            else:
                print(f"- {thread.name} with {thread.native_id} has ended.")
        print("\n")

    def list_active_processes(self):
        """Provides an overview of all running subprocesses."""
        print("\nActive Subprocesses:")
        for process in self.processes:
            if isinstance(process, multiprocessing.Process):
                if process.is_alive():
                    print(f"- Prozess {process.pid} in process.")
                else:
                    print(f"- Prozess {process.pid} has ended.")
            elif isinstance(process, subprocess.Popen):
                if process.poll() is None:
                    print(f"- Prozess {process.pid} in process.")
                else:
                    print(f"- Prozess {process.pid} has ended.")
            else:
                print(f"- Unknown process.")
        print("\n")

    def cleanup(self):
        """Removes terminated threads and processes from the lists."""
        self.threads = [t for t in self.threads if t.is_alive()]
        self.processes = [
            p for p in self.processes 
            if (isinstance(p, multiprocessing.Process) and p.is_alive()) or 
            (isinstance(p, subprocess.Popen) and p.poll() is None)
            ]

# Create global instance
PM = ProcessManager()

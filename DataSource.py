### Import der Python-Module
import time
import threading
import pandas as pd
from tkinter import messagebox

import sys
print(sys.executable)
import serial
import serial.tools.list_ports

print(f"Serial-Modul: {serial.__file__}")

### Own modules
from Instance_Manager import IM
from Process_Manager import PM

class DataSource:
    def __init__(self, sensors):
        self.logger = IM.get_instance("logger")
        self.logger.info(f"An instance of DataSource has been created: {self} with type: {type(self)}")
        self.source = None  # Default source
        self.data = pd.DataFrame(columns=["timestamp", "temperature"])   # Placeholder for data
        self.csv_file = "Messdaten.csv"  # File path for simulation
        self.serial_port = None
        self.stop_csv_thread = False
        self.stop_ser_thread = False
        self.thread = None
        self.lock = threading.Lock()
        self.sensors = sensors
        self.EB = IM.get_instance("EB") # EventBus
        self.EB.subscribe("data_source_changed", self.set_source)
        self.EB.subscribe("comport_selected", self.set_source)
        self.EB.subscribe("window_close", self.stop_reading)

    def stop_reading(self, data=None):
        '''Stops any running thread for reading data from the selected source.'''
        self.stop_csv_thread = True
        self.stop_ser_thread = True

    def stop_live_thread(self, data=None):
        '''Terminates the running thread and closes the serial interface if it is still open.'''
        self.stop_ser_thread = True
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

    def set_source(self, source):
        '''Sets the data source and starts the appropriate reading thread.'''
        self.stop_reading()  # Ends the current thread
        self.source = source
        if self.source.startswith("COM"):
            self.selected_port = self.source
            self.source = "Livedata"
            print(f"Neue Datenquelle: {self.source}")
            self.start_reading(self.source, self.selected_port)  # Starts the new thread
        elif self.source == "Livedata":
            if hasattr(self, 'selected_port'):
                self.start_reading(self.source, self.selected_port)
            else:
                ports = list(serial.tools.list_ports.comports())
                if len(ports) == 0:
                    messagebox.showerror("Error", "No COM ports available.")
                else:
                    self.selected_port = ports[0].device
                    self.start_reading(self.source, self.selected_port)
        elif self.source is None:
            self.logger.warning("No data source selected.")
        else:
            self.logger.info(f"New data source: {self.source}")
            self.start_reading(self.source)  # Starts the new thread
    
    def start_reading(self, source, com_port=None):
        '''Starts the appropriate reading thread based on the selected data source.'''
        if hasattr(self, 'proc') and self.proc.poll():
            print(f"Ending process {self.proc}...")
            try:
                self.proc.terminate()  # Process terminated
                print(f"Process {self.proc.ident} terminated.")
            except Exception as e:
                print(f"Error when terminating the process: {self.proc.name} with type: {type(e)}")
                self.logger.error(f"Error when terminating the process: {self.proc.name} with type: {type(e)}")
        if source == "Livedata":
            self.stop_reading()
            self.start_serial_reading(com_port)
        elif source == "Simulation":
            self.stop_live_thread()
            self.start_csv_reading()
        else:
            self.logger.warning(f"Unknown data source: {source}")


    def start_csv_reading(self):
        print("Starte CSV-Lesevorgang")
        creatingData = "GenerateMeasurementData.py"
        self.proc = PM.start_subprocess(creatingData)
        print(f"Started subprocess with PID: {self.proc.pid}")
        self.logger.info(f"Display subprocesses: {self.proc.stdout}, Error: {self.proc.stderr}, Return value: {self.proc.returncode}")
        def read_csv():
            while not self.stop_csv_thread:
                try:
                    new_data = pd.read_csv(self.csv_file, header = None, names = ["timestamp", "temperature"])
                    new_data["timestamp"] = pd.to_datetime(new_data["timestamp"])
                    with self.lock:
                        self.data = new_data
                except Exception as e:
                    self.logger.error(f"Error while reading  CSV-file: {e} with type: {type(e)}")
                try:
                    # HACK: enumerate scheint üerbflüssig zu sein. GGF. inklusive des i's entfernen.
                    for i, sensor in enumerate(self.sensors):
                        if len(self.data) == 0:
                            print("No data in CSV-file.")
                            continue
                        else:
                            current_value = self.data.iloc[-1]['temperature']
                            sensor.update_temp_value(float(current_value))
                            sensor.update_measurement_data(float(current_value))
                except Exception as e:
                    print(f"Error while publishing data {self.data} from csv file {type(self.data)}: {e} with type: {type(e)}")
                time.sleep(1)  # Data refresh interval
            
        self.stop_csv_thread = False
        PM.start_thread(read_csv, "read_csv", daemon=True)
        # print(f"CSV reading thread started.")

    def start_serial_reading(self, com_port):      
        self.selected_port = com_port

        def read_from_port(ser):
            print(f"Connected to comport: {ser}. Start reading...")
            while not self.stop_ser_thread:
                if ser.is_open:
                    try:
                        self.data = ser.readline().decode('utf-8').strip()
                        self.data = self.data.split()
                        self.data = [float(temp) for temp in self.data]
                        for i, temp in enumerate(self.data):
                            if temp >= 100 or temp <= -100:
                                self.sensors[i].is_connected = False
                            else:
                                self.sensors[i].is_connected = True
                    except Exception as e:
                        self.logger.warning(f"Error while reading: {e}")
                        break
                    try:
                        for i, temp in enumerate(self.data):
                            self.sensors[i].update_measurement_data(float(temp))
                            self.sensors[i].update_temp_value(float(temp))
                    except Exception as e:
                        print(f"Error while publishing the data {self.data} read from the port: {e} with type: {type(e)}")
                        self.logger.warning(f"Error while publishing the data {self.data} read from the port: {e} with type: {type(e)}")
                        break
                time.sleep(0.05)
            self.ser.close()   

        if self.selected_port:
            try:
                print(f"Connecting with COM-Port: {self.selected_port}")
                self.ser = serial.Serial(self.selected_port, 115200) 

                self.stop_ser_thread = False
                PM.start_thread(target = read_from_port, args=(self.ser,), name = "read_from_port", daemon=True)
                
            except serial.SerialException as e:
                messagebox.showerror("Error", f"Failed to connect to COM port: {e}")

        

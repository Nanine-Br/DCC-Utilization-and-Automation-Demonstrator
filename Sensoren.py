### Import der Python-Module
import pandas as pd
from datetime import datetime as dt
from lxml import etree
from scipy.optimize import curve_fit
import numpy as np
import threading
### Own modules
from Global import folder_path, SensorDCC_Dict, number_of_measurement_values_used_in_plot
from Instance_Manager import IM
from Process_Manager import PM
 

class Sensor:
    def __init__(self, name):
        self.EB = IM.get_instance("EB")
        self.EB.subscribe("DCC_toggle_switch_changed", self.DCC_loading_and_calculation)
        self.EB.subscribe("DCC_included", self.include_DCC)
        self.EB.subscribe("schema_is_valid", self.set_schema_validity)
        self.EB.subscribe("min_max_temp_is_set", self.set_min_max_temp)
        self.EB.subscribe("mode_changed", self.set_mode)
        self.sensor_id = name
        self.tab = None
        self.id = None
        self.ylim = None
        # Raw measurement data
        self.current_meas_value = 0
        self.measurementData = pd.DataFrame({"timestamp": [pd.NaT]*number_of_measurement_values_used_in_plot,"temperature": [np.nan]*number_of_measurement_values_used_in_plot})
        self.is_connected = False
        self.DCC_file = "\\".join([folder_path, SensorDCC_Dict[self.sensor_id]])
        # DCC included
        self.corrected_data_df = pd.DataFrame({"timestamp": [pd.NaT]*number_of_measurement_values_used_in_plot,"temperature": [np.nan]*number_of_measurement_values_used_in_plot})
        self.DCC_is_included = False
        self.corrected_temp = 0
        self.a = 0
        self.b = 0
        self.schema_is_valid = None

    #--- General methods ---
        
    def set_mode(self, data):
        self.mode = data

    def get_name(self):
        return self.sensor_id
    
    def calculate_ylim(self):
        if self.DCC_is_included:
            if isinstance(self.measurementData, pd.DataFrame) and len(self.measurementData) > 0:
                min_temp = self.measurementData['temperature'].tail(number_of_measurement_values_used_in_plot).min()
                max_temp = self.measurementData['temperature'].tail(number_of_measurement_values_used_in_plot).max()
            if isinstance(self.corrected_data_df, pd.DataFrame) and len(self.corrected_data_df) > 0:
                min_temp_corr = self.corrected_data_df['temperature'].tail(number_of_measurement_values_used_in_plot).min()
                max_temp_corr = self.corrected_data_df['temperature'].tail(number_of_measurement_values_used_in_plot).max()
            
            if 'min_temp_corr' in locals() and 'max_temp_corr' in locals() and 'min_temp' in locals() and 'max_temp' in locals():
                min_temp = min(min_temp, min_temp_corr)
                max_temp = max(max_temp, max_temp_corr)
                self.ylim = (min_temp, max_temp)

                return self.ylim
        else:
            return None
    
    #--- Measurement methods ---
    
    def get_temp_value(self):
        return self.current_meas_value
    
    def update_temp_value(self, new_value):
        self.current_meas_value = new_value
        
    def get_measurement_data(self):
        return self.measurementData

    def update_measurement_data(self, temperature):
        self.temperature = temperature
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = pd.to_datetime(timestamp)
        new_data = [timestamp, self.temperature]

        self.measurementData.loc[len(self.measurementData)] = new_data

    #--- DCC methods ---

    def update_DCC_measurement_data(self, corrected_value):
        self.corrected_temp = corrected_value
        last_index = len(self.measurementData) - 1
        timestamp = self.measurementData.iloc[last_index]['timestamp']
        timestamp = pd.to_datetime(timestamp)

        if timestamp != self.corrected_data_df.iloc[-1]['timestamp']:
            new_data = [timestamp, self.corrected_temp]

            self.corrected_data_df.loc[len(self.corrected_data_df)] = new_data  

        
    def get_DCC_measurement_data(self):
        return self.corrected_data_df   

    def _get_list_from_string(string):
        return [float(x) for x in string.split()]  

    def fit_func(x, a, b):
            return b * x + a
    
    def calc_y_correction(self, t_ref):
        return (t_ref * self.b + self.a)
    
    def calc_c_b(self, messwert):
        return -(messwert - self.a) / self.b**2
    
    def find_u_calc(self, messwert, mes_temp_c, uncertainty):
        dataframe = pd.DataFrame({"mes_temp_c": mes_temp_c, "uncertainty": uncertainty})
        dataframe["abstand"] = abs(dataframe["mes_temp_c"] - messwert)
        min_abstand = dataframe["abstand"].min()
        index_of_min_abstand = dataframe[dataframe["abstand"] == min_abstand].index[0]
        uncertainty_of_min_abstand = dataframe["uncertainty"][index_of_min_abstand]/2
        return uncertainty_of_min_abstand
    
    def _get_list_from_string(string):
        return [float(x) for x in string.split()]
    
    def set_schema_validity(self, schema_is_valid):
        self.schema_is_valid = schema_is_valid

    def include_DCC(self, data):
        instance = data["ID"] # ID of switch
        value = data["value"] # Value of switch
        filepath = data["filename"]
        if instance == self.id:
            self.DCC_is_included = value
            self.calc_correction(filepath)
    
    def DCC_loading_and_calculation(self, data):
        instance = data["ID"] # ID des Switches
        value = data["value"] # Wert des Switches
         
        if instance == self.id:
            self.DCC_is_included = value
            if value:
                try:
                    IM.get_instance("Gui").dropDCClabel.config(text="Please drag & drop a DCC")
                except Exception as e:
                    print(f"Sensor {self.sensor_id}: Fehler beim laden der GUI Instanz: {e}")
                try:
                    # import DCCvalidation as DCCv
                    from DCCvalidation import performDCCvalidation
                    def validate_DCC_file():
                        performDCCvalidation(self.DCC_file, self.mode, self.id)
                    
                    validation_thread = PM.start_thread(target=validate_DCC_file, name="DCC_validation_thread")
                    print(f"Für den Sensor {self.sensor_id} wurde der {validation_thread} gestartet.")

                except Exception as e:
                    print(f"Sensor {self.sensor_id}: Fehler beim Validieren der DCC-Datei: {e}")
            
                self.calc_correction(self.DCC_file)
           
        
    def calc_correction(self, dccFile):
        ns = {
            'dsig': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#',
            'ecdsa': 'http://www.w3.org/2001/04/xmldsig-more#',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'dcc': "https://ptb.de/dcc",
            'si': "https://ptb.de/si"
            }

        try:
            tree = etree.parse(dccFile)
            self.root = tree.getroot()
        except Exception as e:
            print(f"Sensor {self.sensor_id}: Fehler beim Parsen der DCC-Datei {dccFile}: {e}")
        
        try:
            self.ref_temp_c = Sensor._get_list_from_string(self.root.xpath("//dcc:quantity[contains(@refType,'basic_referenceValue')]//si:realListXMLList[si:unitXMLList='\\degreecelsius']/si:valueXMLList/text()", namespaces=ns)[0])
            self.mes_temp_c = Sensor._get_list_from_string(self.root.xpath("//dcc:quantity[contains(@refType,'basic_measuredValue')]//si:realListXMLList[si:unitXMLList='\\degreecelsius']/si:valueXMLList/text()", namespaces=ns)[0])
            self.dev_temp_c = Sensor._get_list_from_string(self.root.xpath("//dcc:quantity[@refType='basic_measurementError']/si:realListXMLList/si:valueXMLList/text()", namespaces=ns)[0])
            self.uncertainty = Sensor._get_list_from_string(self.root.xpath("//dcc:quantity[@refType='basic_measurementError']//si:uncertaintyXMLList/text()", namespaces=ns)[0])
            try:
                self.s_hyst = float(self.root.xpath("//dcc:metaData[contains(@refType,'temperature_hysteresis')]//si:valueStandardMUXMLList/text()", namespaces=ns)[0])
            except:
                try:
                    self.hyst = float(self.root.xpath("//dcc:quantity[contains(@refType,'temp_hysteresisImpact')]//si:valueXMLList/text()", namespaces=ns)[0])
                    self.s_hyst = self.hyst / np.sqrt(3)
                except:
                    self.s_hyst = 0.024
            
            # Calibration fit
            popt, pcov = curve_fit(Sensor.fit_func, self.ref_temp_c, self.mes_temp_c)
            self.a, self.b = popt[0], popt[1]
            perr = np.sqrt(np.diag(pcov))
            self.s_a, self.s_b = perr[0], perr[1]
            self.corrected_y = [self.calc_y_correction(x) for x in self.ref_temp_c]
            self.s_R = np.sqrt((sum(list(map(lambda x,y: (x-y)**2, self.mes_temp_c, self.corrected_y)))) / (len(self.mes_temp_c)-2))
            # Calculate sensivity factors (constant)
            self.c_a = -1 / self.b
            self.c_hyst = 1
            self.c_R = 1
            # Calculate uncertainty contributions
            self.u_a = self.c_a * self.s_a
            self.u_hyst = self.c_hyst * self.s_hyst
            self.u_R = self.c_R * self.s_R

        except Exception as e:
            print(f"Sensor {self.sensor_id}: Error while reading DCC-file: {e}")
            
        try:
            self.DCCdata = pd.DataFrame({"ref_temp_c": self.ref_temp_c, "mes_temp_c": self.mes_temp_c, "dev_temp_c": self.dev_temp_c, "uncertainty": self.uncertainty})
            self.EB.publish("DCC_data_loaded", {"ID": self.id, "df": self.DCCdata, "a": self.a, "b": self.b})
        except Exception as e:
            print(f"Sensor {self.sensor_id}: Error while creating DataFrames: {e}")

    def set_min_max_temp(self, data):
        current_sensor = data["name"].sensor_id
        if current_sensor == self.sensor_id:
            self.min_temp = data["min_temp"]
            self.max_temp = data["max_temp"]

    def check_min_max_temp(self):
            if self.current_meas_value < self.min_temp or self.current_meas_value > self.max_temp:
                self.EB.publish("temp_out_of_range", {"ID": self.id, "value": self.current_meas_value, "min_temp": self.min_temp, "max_temp": self.max_temp})
                return False
            else:
                return True
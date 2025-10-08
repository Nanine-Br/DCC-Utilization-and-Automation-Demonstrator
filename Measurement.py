### Import of Python-Moduls
import numpy as np
### Own Moduls
from Instance_Manager import IM


class MeasurementDataCalculated:
    def __init__(self):
        ### Import der Instanzen
        self.CC = IM.get_instance("CC")
        EB = IM.get_instance("EB")
        EB.subscribe("limit_changed", self.update_input_limits_dict)
        EB.subscribe("DCC_toggle_switch_changed", self.update_switches)
        EB.subscribe("calibration_intervall_changed", self.update_calibrationIntervall)
        self.DCCswitches = {}
        self.input_limits_dict = {}
        self.output_limits_dict = {}
        self.initialize_input_limits_dict(self.CC.get_sensors())
    
    def initialize_input_limits_dict(self, sensors):
        for sensor in sensors:
            print(f"Initializing limits for sensor: {sensor.get_name()}")
            self.input_limits_dict[f"{sensor.get_name()}_Upper Limit"] = 0
            self.input_limits_dict[f"{sensor.get_name()}_Lower Limit"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Upper Limit of Acceptance"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Lower Limit of Acceptance"] = 0
            self.input_limits_dict["Calibration Intervall"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Specification"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Acceptance Band Width"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Upper Limit of Acceptance DCC"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Lower Limit of Acceptance DCC"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Corrected Temp"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Uncertainty"] = 0
            self.output_limits_dict[f"{sensor.get_name()}_Acceptance Band Width DCC"] = 0

    def update_switches(self, data):
        instance = data["ID"]
        value = data["value"]
        self.DCCswitches[instance] = value
    
    def update_input_limits_dict(self, data):
        instance = data["instance_id"]
        type_of_instance = instance.split("_")[0]
        number_of_instance = instance.split("_")[1]
        sensor = self.CC.get_sensors()[int(number_of_instance)]
        self.input_limits_dict[sensor.get_name() + "_" + type_of_instance] = data["value"]
        self.update_limits_of_acceptance(sensor)
    
    def update_limits_of_acceptance(self, sensor):
        upper_limit = self.input_limits_dict[sensor.get_name() + "_Upper Limit"]
        lower_limit = self.input_limits_dict[sensor.get_name() + "_Lower Limit"]
        specification_uncertainty = self.calculate_specification(sensor.get_temp_value())            
        upper_limit_acceptance, lower_limit_acceptance = self.calculate_acceptance_limits(upper_limit, lower_limit, specification_uncertainty)
        band_width = round(upper_limit_acceptance - lower_limit_acceptance, 2)
        self.update_output_limits_dict(sensor.get_name() + "_Upper Limit of Acceptance", upper_limit_acceptance)
        self.update_output_limits_dict(sensor.get_name() + "_Lower Limit of Acceptance", lower_limit_acceptance)
        self.update_output_limits_dict(sensor.get_name() + "_Specification", specification_uncertainty)
        self.update_output_limits_dict(sensor.get_name() + "_Acceptance Band Width", band_width)
    
    def update_output_limits_dict(self, instance, value):
        self.output_limits_dict[instance] = value
    
    def calculate_acceptance_limits(self, upper_limit, lower_limit, specification_uncertainty):
        upper_limit_acceptance = upper_limit - specification_uncertainty
        lower_limit_acceptance = lower_limit + specification_uncertainty
        return upper_limit_acceptance, lower_limit_acceptance
    
    def calculate_specification(self, temp):
        return round(np.sqrt((0.15+0.002*abs(float(temp)))**2+0.5**2), 2)
    
    def update_specification(self):
        for sensor in self.CC.get_sensors():
            self.update_output_limits_dict(sensor.get_name() + "_Specification", self.calculate_specification(sensor.get_temp_value()))

    def update_calibrationIntervall(self, value):
        self.input_limits_dict["Calibration Intervall"] = value
        

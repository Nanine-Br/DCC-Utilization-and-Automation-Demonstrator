### Import own modules
from Instance_Manager import IM
from Global import max_number_of_sensors
from DataRefreshing import LivePlotApp as LPA

class CentralController:
    def __init__(self):
        self.EB = IM.get_instance("EB")
        self.logger = IM.get_instance("logger")
        self.max_number_of_sensors = max_number_of_sensors
        self.sensorNamesList = [f"Sensor {i+1}" for i in range(self.max_number_of_sensors)]
        self.logger.info(f"SensorNamesList: {self.sensorNamesList}")
        # Creation of sensor instances
        from Sensoren import Sensor
        self.sensors = [Sensor(name) for name in self.sensorNamesList]
        self.logger.info(f"Sensor-Instanzen erstellt: {self.sensors}")
        # Set ID for each sensor
        for i, sensor in enumerate(self.sensors):
            sensor.id = i
        self.EB.publish("sensors_created", self.sensors)
        # Creation of Instance of DataSource
        from DataSource import DataSource as DS
        self.DS = DS(self.sensors)
        IM.set_instance("DS", self.DS)
        # Lists for intances
        self.live_plot_apps = []
        self.DCCplotApps = []
        self.connected_sensors = []

    def update_connected_sensors(self):
        self.connected_sensors = [sensor.is_connected for sensor in self.sensors]
    
    def get_connected_sensors(self):
        return self.connected_sensors
    
    def create_plot_apps(self, sensor, parent):
        plotApp = LPA(sensor, parent)
        self.live_plot_apps.append(plotApp)
        return plotApp

    def create_DCCplot_apps(self, sensor, parent):
        DCCplotApp = LPA(sensor, parent)
        self.DCCplotApps.append(DCCplotApp)
        return DCCplotApp

    def update_limits_dict(self, instance, value):
        self.input_limits_dict[instance] = value

    def get_sensors(self):
        return self.sensors

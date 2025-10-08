### Import of Python-Modules
import sys
import os
import ttkbootstrap as tkboot
from tkinterdnd2 import TkinterDnD, DND_FILES
from functools import partial
import numpy as np

print("Program starting --> GUI will be opened soon...")

# ----- Custom modules & instantiation of classes -----
# Instantiation of InstanceManagers
from Instance_Manager import IM
# Loading classes with no additional dependencies
from Process_Manager import PM # ProcessManager
from EventBus import EventBus
from Logger import myLogger
logger_main = myLogger.getLogger(name="Mainlogger", path="Demonstrator_file.log")

# Registration of instances
IM.set_instance("logger", logger_main)
IM.set_instance("EB", EventBus())

# Importing classes with additional dependencies
from CentralControl import CentralController
from Measurement import MeasurementDataCalculated

IM.set_instance("CC", CentralController())
IM.set_instance("MD", MeasurementDataCalculated())

## Import needed instances
EB = IM.get_instance("EB")  # EventBus
CC = IM.get_instance("CC")  # CentralController
MD = IM.get_instance("MD")  # MeasurementDataCalculated

# Ensure that the DLLs are found in the EXE build
if getattr(sys, 'frozen', False):  # Check whether the program runs as an EXE file
    os.environ['PATH'] = os.path.dirname(sys.executable) + os.pathsep + os.environ['PATH']

# ------------ Fuctions ------------
def on_closing(root):
    '''On the event of closing the window, all threads and processes are stopped and the program is completely exited.'''
    EB.publish("window_close", None)
    PM.list_active_processes()
    PM.list_active_threads()
    root.destroy()  # Closes the window
    print("-->GUI stopped")
    sys.exit()  # Terminate the program completely


def update_display_fields(gui, sensor, upper_limit, lower_limit, upper_limit_acceptance, lower_limit_acceptance, m_value, specification, band_width):
    '''Updates the display fields in the GUI with the measurement data and changes the LED color based on the measurement value.'''
    counter = sensor.id
    gui.output_upper_acceptance[counter].update_output_field(upper_limit_acceptance)
    gui.output_lower_acceptance[counter].update_output_field(lower_limit_acceptance)
    gui.output_measured_temps[counter].update_output_field(m_value)
    gui.output_specifications[counter].update_output_field(specification)
    gui.band_width_list[counter].update_output_field(band_width)
    if m_value > upper_limit or m_value < lower_limit:
        gui.leds[counter].update_color("red")
    elif m_value >= upper_limit_acceptance and m_value <= upper_limit or m_value <= lower_limit_acceptance and m_value >= lower_limit:
        gui.leds[counter].update_color("yellow")
    elif m_value < upper_limit_acceptance and m_value > lower_limit_acceptance:
        gui.leds[counter].update_color("lightgreen")
    else:
        gui.leds[counter].update_color("black")
    

def calc_combined_uncertainty(self, c_b, u_cal):
    '''Calculates the combined uncertainty based on the provided parameters.'''
    return np.sqrt((self.c_a * self.s_a)**2 + (c_b * self.s_b)**2 + (u_cal)**2 + (self.u_hyst)**2 + (self.u_R)**2)


def update_DCC_display_fields(gui, sensor, upper_limit, lower_limit, corrected_value, exp_uncertainty, upper_limit_acceptance_DCC, lower_limit_acceptance_DCC, dcc_band_width):
    '''Updates the DCC display fields in the GUI with the corrected measurement data and changes the LED color based on the corrected measurement value.'''
    counter = sensor.id
    gui.corrected_temps[counter].update_output_field(corrected_value)
    gui.uncertainties[counter].update_output_field(exp_uncertainty)
    gui.output_upper_acceptanceDCC [counter].update_output_field(upper_limit_acceptance_DCC)
    gui.output_lower_acceptanceDCC [counter].update_output_field(lower_limit_acceptance_DCC)
    gui.band_width_list_DCC[counter].update_output_field(dcc_band_width)
    if corrected_value > upper_limit or corrected_value < lower_limit:
        gui.ledsDCC[counter].update_color("red")
    elif corrected_value >= upper_limit_acceptance_DCC and corrected_value <= upper_limit or corrected_value <= lower_limit_acceptance_DCC and corrected_value >= lower_limit:
        gui.ledsDCC[counter].update_color("yellow")
    elif corrected_value < upper_limit_acceptance_DCC and corrected_value > lower_limit_acceptance_DCC:
        gui.ledsDCC[counter].update_color("lightgreen")
    else:
        gui.ledsDCC[counter].update_color("black")


def update_gui(data, gui):
    '''Updates the GUI with the latest measurement data from the sensors, calcualtes the limits and refreshes the plots accordingly.'''

    def update():
        while True:
            for i, (sensor, liveplotApp) in enumerate(zip(CC.get_sensors(), CC.live_plot_apps)):
                data_df = sensor.get_measurement_data()
                m_value = round(sensor.get_temp_value(), 4)
                specification = MD.calculate_specification(m_value)
                upper_limit = MD.input_limits_dict[sensor.get_name() + "_Upper Limit"]
                lower_limit = MD.input_limits_dict[sensor.get_name() + "_Lower Limit"]
                upper_limit_acceptance = round(MD.output_limits_dict[sensor.get_name() + "_Upper Limit of Acceptance"], 2)
                lower_limit_acceptance = round(MD.output_limits_dict[sensor.get_name() + "_Lower Limit of Acceptance"], 2)
                band_width = round(MD.output_limits_dict[sensor.get_name() + "_Acceptance Band Width"], 2)
                update_display_fields(gui, sensor, upper_limit, lower_limit, upper_limit_acceptance, lower_limit_acceptance, m_value, specification, band_width)
                
                ylim = sensor.calculate_ylim()
                if ylim is not None:
                    ylim = (min(ylim[0], lower_limit - 0.5), max(ylim[1], upper_limit + 0.5))   
                
                liveplotApp.update_plot(data_df, upper_limit, lower_limit, upper_limit_acceptance, lower_limit_acceptance, "Standard temperature measurement", ylim)

                EB.publish("plot_generated", liveplotApp)

                if sensor.DCC_is_included:
                    try:
                        temp_in_calc_range = sensor.check_min_max_temp()
                    except:
                        logger_main.error(f"An error occurred while checking the temperature ranges. Error: {sys.exc_info()[0]}")
                        continue
                    
                    if temp_in_calc_range:
                        counter = i
                        k = 2
                        a = sensor.a
                        b = sensor.b
                        mess_temp = sensor.mes_temp_c
                        uncertainties = sensor.uncertainty
                        c_a = sensor.c_a
                        s_a = sensor.s_a
                        s_b = sensor.s_b
                        u_hyst = sensor.u_hyst
                        u_R = sensor.u_R

                        corrected_value = round((m_value - a) / b, 5)
                        sensor.update_DCC_measurement_data(corrected_value)
                        corrected_value = round(corrected_value, 2)
                        c_b = sensor.calc_c_b(m_value)
                        u_b = c_b * s_b
                        u_cal = sensor.find_u_calc(m_value, mess_temp, uncertainties)
                        combined_uncertainty = round(np.sqrt((c_a * s_a)**2 + (u_b)**2 + (u_cal)**2 + (u_hyst)**2 + (u_R)**2), 2)
                        exp_uncertainty = round(combined_uncertainty * k, 2)
                        upper_limit_acceptance_DCC = round(upper_limit - exp_uncertainty, 2)
                        lower_limit_acceptance_DCC = round(lower_limit + exp_uncertainty, 2)
                        corrected_data_df = sensor.get_DCC_measurement_data()
                        dcc_band_width = round(upper_limit_acceptance_DCC - lower_limit_acceptance_DCC, 2)
                        update_DCC_display_fields(gui, sensor, upper_limit, lower_limit, corrected_value, exp_uncertainty, upper_limit_acceptance_DCC, lower_limit_acceptance_DCC, dcc_band_width)
                        CC.DCCplotApps[counter].update_plot(corrected_data_df, upper_limit, lower_limit, upper_limit_acceptance_DCC, lower_limit_acceptance_DCC, "Metrologically traceable temperature measurement", ylim)
                        
                        EB.publish("plot_generated", CC.DCCplotApps[counter])
  
                    else:
                        EB.publish("DCC_temp_range_error", {"ID": sensor.id, "value": False})
                        sensor.DCC_is_included = False
                
                if not sensor.DCC_is_included and gui.DCCswitsches[i].toggle_var.get():
                    if sensor.check_min_max_temp():
                        EB.publish("DCC_temp_range_error", {"ID": sensor.id, "value": True})
                        sensor.DCC_is_included = True
                    else:
                        continue              

    for thread in PM.threads:
        if thread.name == "update_thread":
            return
    thread = PM.start_thread(update, name="update_thread")

def main_instanz_handler(data, gui):
    '''Transfers the measurement data, as well as instances of the GUI and the controller, to the data processing functions.'''
    update_gui(data, gui)


# Import of the GUI after all other classes are defined to avoid circular dependencies
import DemonstratorGUI as GUI

def draw_the_canvas(liveplotApp):
    liveplotApp.canvas.draw()
    liveplotApp.ax.figure.canvas.flush_events()


def main():
    '''Main function to start the GUI, update it in the mainloop and orchestrate data from different scripts.'''
    root = TkinterDnD.Tk()
    root.tk.call("tk", "scaling", 1.5) 
    style = tkboot.Style("cosmo")
    style.master = root
    root.state("zoomed") # Start maximized
    
    Gui = GUI.DCCDemonstratorGUI(root, CC)
    IM.set_instance("Gui", Gui)
    
    logger_main.info("Die GUI wurde gestartet")
    print("---->GUI started")
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))

    instanz_handler = partial(main_instanz_handler, gui=Gui)

    EB.subscribe("data_source_changed", instanz_handler)
    EB.subscribe("comport_selected", instanz_handler)
    EB.subscribe("plot_generated", draw_the_canvas)
    
    root.mainloop()

# Start program
if __name__ == "__main__":
    print("Almost there...")
    main()

    
    
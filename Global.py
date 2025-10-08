# ------------------------ Global constants used in all modules ------------------------

###############
##  General  ##
###############
max_number_of_sensors = 4

##############
## Gemoetry ##
##############
# Text-Widgets
text_widget_font_size = 15
text_widget_font = "Arial"
# text_widget_font = "Helvetica"
header_font_size = 18
# Logo
image_max_size = (553 * 0.5, 336 * 0.5)
image_min_size = (165, 100)
image_ratio = 553/336
# Plots
faktor = 130 # 115 Pixel pro Zoll
plot_fig_size = (7, 6) # in Zoll
plot_font = "Arial"
number_of_measurement_values_used_in_plot = 50
placeholder_size = 1000 # in Pixeln 
canvas_size = (int(plot_fig_size[0] * faktor), int(plot_fig_size[1] * faktor)) # in Pixeln
# Tabs
tab_text_size = 30

###############
## DCC-Files ##
###############
SensorDCC_Dict = {
    "Sensor 1": "8.1I1539A_SEALED.xml",
    "Sensor 2": "8.1I1539B_SEALED.xml",
    "Sensor 3": "8.1I1539C_SEALED.xml",
    "Sensor 4": "8.1I1539D_SEALED.xml"
    }

Sensor_Name_dict = {
    "Sensor 1": "Temperature Sensor 1b",
    "Sensor 2": "Temperature Sensor 2",
    "Sensor 3": "Temperature Sensor 3",
    "Sensor 4": "Temperature Sensor 4b"
    }

folder_path = "DCCs"
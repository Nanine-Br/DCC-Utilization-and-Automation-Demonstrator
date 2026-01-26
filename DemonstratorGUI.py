from tkinter import messagebox
import tkinter as tk
from PIL import Image, ImageTk
import serial.tools.list_ports
import ttkbootstrap as tkboot
import threading
from tkinterdnd2 import DND_FILES
from tkinter.scrolledtext import ScrolledText
import os
# Import of own modules
from Instance_Manager import IM
from Process_Manager import PM
from Widgets import LEDwidget, SwitchWidget, PlaceholderWidget, InputFieldWidget, OutputFieldWidget
from Global import text_widget_font_size, header_font_size, text_widget_font, image_max_size, image_min_size, tab_text_size, canvas_size
import DCCvalidation as DCCv


class DCCDemonstratorGUI:
    def __init__(self, master, controller):
        self.MD = IM.get_instance("MD")
        self.EB = IM.get_instance("EB")
        self.logger = IM.get_instance("logger")
        self.controller = controller
        self.master = master
        self.master.title("DCC Demonstrator")
        self.mode = None
    #TODO: Resize Funktion ist raus --> Listen, Widgets und Funktionen auf Notwendigkeit prüfen
        # Lists for Resize-Funktion
        self.labels = []
        self.custom_widgets = []
        # Lists for Instances of the InputFields
        self.input_upper_limits = []
        self.input_lower_limits = []
        self.frames = []
        self.scrollable_frames = []
        ### Lists for intances of the OutputFields ###
        # Without DCC
        self.output_measured_temps = []
        self.output_specifications = []
        self.output_upper_acceptance = []
        self.output_lower_acceptance = []
        self.leds = []
        self.band_width_list = []
        self.raw_measurement_frames = []
        # With DCC
        self.DCCswitsches = []
        self.output_upper_acceptanceDCC = []
        self.output_lower_acceptanceDCC = []
        self.corrected_temps = []
        self.uncertainties = []
        self.ledsDCC = []
        self.ledDCC_label = []
        self.DCC_validation_LEDs = []
        self.validation_frames = []
        self.corrected_measurement_frames = []
        self.placeholder_list = []
        self.band_width_list_DCC = []
        # Additional variables
        self.logo_path = None
        self.user_selected_path = False
        self.default_logo_path = r"BAM_klein.png"
        self.logos = []
        self.corrected_limit_frames = []
        self.corr_middle_frames = []
        self.ledDCC_title_list = []
        self.max_number_of_sensors = 4
        self.sensorNamesList = [f"Sensor {i+1}" for i in range(self.max_number_of_sensors)]
        self.sensors = []
        self.leds_for_validation = []
        self.last_height = self.master.winfo_height()
        self.last_width = self.master.winfo_width()
        self.configure_grid()
        self.create_tabs()
        self.EB.subscribe("DCC_toggle_switch_changed", self.toggle_plot)
        self.EB.subscribe("DCC_temp_range_error", self.handle_temp_range_error)
        self.EB.subscribe("DCC_included", self.toggle_plot)
        self.EB.subscribe("DCC_schema_validation_update", self.update_validation_results)
        self.EB.subscribe("DCC_validation_successful", self.update_sensor_LED)
        self.EB.subscribe("DCC_data_loaded", self.include_DCC_data) 
        
        self.logger.info(f"Die Liste mit den Placeholder-Widgets hat die Länge: {len(self.placeholder_list)} und folgenden Inhalt: {self.placeholder_list}")
        
    def configure_grid(self):
        '''Configuring the grid of the main window'''
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)


    # Global functions for the GUI
    def load_BAM_logo(self, tab, file_path=None, max_size=image_max_size, min_size=image_min_size):
        if file_path:
            self.logo_path = file_path # Update user-defined path
        elif self.logo_path is None:
            self.logo_path = self.default_logo_path # Use default path if no user-defined path is set
        try:            
            pil_image = Image.open(self.logo_path) # Opens the image with Pillow and converts it for tk.PhotoImage
            self.original_image = pil_image    
            self.tk_image = self.scale_image(self.original_image, max_size, min_size)
            image_label = tkboot.Label(tab, image=self.tk_image)
            image_label.photo = self.tk_image  # Save the image as an attribute to prevent garbage collection
            
            return image_label
        
        except Exception as e:
            self.logger.error(f"Error loading the BAM logo: {e}")
            style = tkboot.Style()
            style.configure("Placeholder.TLabel", background="green", foreground="white")
            placeholder = tkboot.Label(tab, text='BAM Logo not found!', style="Placeholder.TLabel")
            placeholder.grid(rowspan=8, column=0, sticky="w", padx=5, pady=5)
            return placeholder

    def scale_image(self, image, max_size, min_size):
            # Calculate the aspect ratio of the image
            original_width, original_height = image.size
            max_width, max_height = max_size

            # Calculate the scaling factors.
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_ratio = min(width_ratio, height_ratio)

            # Calculate the new size of the image
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

            if new_width < min_size[0] or new_height < min_size[1]:
                new_width = min_size[0]
                new_height = min_size[1]

            # Scaling the image to the calculated size
            self.resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(self.resized_image)

    
    #### ------------- GUI structure ------------- ####
    def create_tabs(self):
        self.tab_control = tkboot.Notebook(self.master)
        self.tab_control.grid(row=0, column=0, sticky='nsew')
        self.create_settings_tab()
        self.create_overview_tab()
        self.create_sensor_tabs()
        self.tabs = self.tab_control.winfo_children()
        self.logger.info(f"Die Tabs wurden erfolgreich erstellt: {self.tabs}")
        
    def create_settings_tab(self):
        self.tab = tkboot.Frame(self.tab_control)
        self.tab_control.add(self.tab, text="Settings")   
        self.label_style = tkboot.Style()
        self.label_style.configure("GUI.TLabel", font=("Helvetica", tab_text_size))

        # Selecting the data source
        self.source_label = tkboot.Label(self.tab, text="Select Data Source:", style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
        self.labels.append(self.source_label)
        self.source_label.grid(row=0, column=0, padx=10, pady=10, sticky=tkboot.NW)
        self.source_var = tkboot.StringVar()
        self.source_live = tkboot.Radiobutton(self.tab, text="Livedata",  value="Livedata", width=20,  variable=self.source_var, command=lambda: self.on_data_source_change(value="Livedata", event="data_source_changed"))
        self.source_live.grid(row=0, column=1, padx=10, pady=10, sticky=tkboot.W)
        self.source_sim = tkboot.Radiobutton(self.tab, text="Simulation", value="Simulation", variable=self.source_var, command=lambda: self.on_data_source_change(value="Simulation", event="data_source_changed"))
        self.source_sim.grid(row=0, column=2, padx=10, pady=10, sticky=tkboot.W)

        # Refresh button     
        self.refresh_button = tkboot.Button(self.tab, text="Refresh COM Ports", command=self.refresh_com_ports)
        self.refresh_button.grid(row=1, column=3, padx=10, pady=10, sticky=tkboot.W)
            
        # Selecting the COM-Port
        self.com_port_label = tkboot.Label(self.tab, text="Select COM Port:", style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
        self.labels.append(self.com_port_label)
        self.com_port_label.grid(row=1, column=0, padx=10, pady=10, sticky=tkboot.NW)
        # Retrieve a list of available COM ports & create a drop-down menu
        com_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not com_ports:
            com_ports.insert(0, "No connection found")
        self.com_port_var = tkboot.StringVar()
        self.com_port_combobox = tkboot.Combobox(self.tab, textvariable=self.com_port_var, values=com_ports)
        self.com_port_combobox.bind("<<ComboboxSelected>>", lambda event: self.on_data_source_change(value="Livedata", event="comport_selected"))
        self.com_port_combobox.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky=tkboot.NW)

        # --------- Calibration intervall ------------
        # Label for entering the calibration interval
        self.label = tkboot.Label(self.tab, text = "Set the calibration intervall\n(in month)", font=(text_widget_font, text_widget_font_size))
        self.label.grid(row=2, column=0, padx=5, pady=5, sticky=tkboot.NW)
        # Input field for the calibration interval
        self.input_value = tkboot.DoubleVar()
        self.calibration_intervall_label = tk.Entry(self.tab, textvariable = self.input_value, width=15, bd=2, relief="sunken", font=(text_widget_font, text_widget_font_size))
        self.calibration_intervall_label.grid(row=3, column=0, padx=5, pady=5, sticky=tkboot.NW)
        self.calibration_intervall_label.bind("<FocusOut>", self.intervall_changed)
        self.calibration_intervall_label.bind("<Return>", self.intervall_changed)
        # Reset button
        self.reset_button = tkboot.Button(self.tab, text="Reset program", command=self.reset_values)
        self.reset_button.grid(row=4, column=0, padx=10, pady=10, sticky=tkboot.W)

    def on_data_source_change(self, value, event):
        self.mode = value
        self.EB.publish("mode_changed", self.mode)
        self.publish_event(event)

        
    def refresh_com_ports(self):
                '''Refreshes the list of available COM ports'''
                com_ports = [port.device for port in serial.tools.list_ports.comports()]
                if not com_ports:
                    com_ports.insert(0, "Keine Verbindung gefunden")
                self.com_port_combobox['values'] = com_ports
                self.com_port_var.set('')

    def intervall_changed(self, event):
            value = self.calibration_intervall_label.get()
            if value.isdigit():
                self.EB.publish("calibration_intervall_changed", value)
            else:
                messagebox.showerror("Error", "Please enter a number")
    
    def reset_values(self):
            '''Resets the output fields on the Validation tab'''
            for led in self.leds_for_validation:
                led.update_color("black")

            self.dcc_validation_display.delete(1.0, tk.END)
            self.dropDCClabel.config(text="Please drag & drop a DCC")

            for switch in self.DCCswitsches:
                state = switch.toggle_var.get()
                if state:
                    switch.toggle_var.set(False)
                    self.MD.update_switches({"ID": switch.id, "value": switch.toggle_var.get()})
                    self.EB.publish("DCC_toggle_switch_changed", {"ID": switch.id, "value": switch.toggle_var.get()})
                    
            if hasattr(self, 'ausgabe'):
                print("Das Ausgabe-Frame wird gelöscht.")
                self.ausgabe.destroy()
            if hasattr(self, 'treeview'):
                print(self.treeview.winfo_exists())
                print("Das Treeview-Widget wird gelöscht.")
                self.treeview.grid_forget()
                self.treeview_frame.grid_forget()
                self.treeview.destroy()
                self.treeview_frame.destroy()
                print(self.treeview.winfo_exists())
            for led in self.DCC_validation_LEDs:
                led.update_color("black")
      

    def create_overview_tab(self):
        self.tab = tkboot.Frame(self.tab_control)
        self.tab_control.add(self.tab, text="DCC Verification")
        self.tab.columnconfigure([0, 1], weight=1)
        logo = self.load_BAM_logo(self.tab)
        self.logos.append(logo)
        logo.grid(row =0, column=0, sticky=tkboot.NSEW)

        # Select DCC via drag and drop
        self.dropDCClabel = tkboot.Label(self.tab, text="Please drag & drop a DCC", relief='solid', anchor="center",  width=35, padding=25, style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
        self.labels.append(self.dropDCClabel)
        self.dropDCClabel.grid(row=1, column=0)
        # Link the drop event to the label
        self.dropDCClabel.drop_target_register(DND_FILES)
        self.dropDCClabel.dnd_bind('<<Drop>>', self.drop)

        # Brief analysis of the DCC
        self.analysis_frame = tkboot.Frame(self.tab, borderwidth=2, relief="solid")
        self.analysis_frame.grid(row=2, rowspan=7, column=0, padx=100, pady=10)
        columns = [0, 1]
        for column in columns:
            self.analysis_frame.columnconfigure(column, weight=1)
        rows = [0, 1, 2, 3, 4, 5, 6, 7]
        for row in rows:
            self.analysis_frame.rowconfigure(row, weight=1)
        self.analysis_label = tkboot.Label(self.analysis_frame, text="DCC verification and receiving inspection", style="GUI.TLabel", anchor="center", font=(text_widget_font, header_font_size))
        self.labels.append(self.analysis_label)
        self.analysis_label.grid(row=3, column=0, columnspan=2, sticky=tkboot.EW, padx=3, pady=3)
        led_labels = ["Schema valid", "DCC integrity", "Issuer Authentic", "Accreditation", "Probe identified and connected", "Calibration not expired", "Calibration covers process window"]
        for i in range(len(led_labels)):
            led = LEDwidget(master=self.analysis_frame, size=0.3, color='black')
            led.canvas.get_tk_widget().grid(row=4+i, column=0, ipadx=0, ipady=0, pady=3, sticky=tkboot.E)
            self.leds_for_validation.append(led)
        for i, text in enumerate(led_labels):
            label = tkboot.Label(self.analysis_frame, text=f"{text}", style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
            self.labels.append(label)
            label.grid(row=4+i, column=1, padx=2, sticky=tkboot.W)

        # self.treeview_frame = tkboot.Frame(self.tab)
        # self.treeview = tkboot.Treeview(self.treeview_frame, selectmode="none")



        # ------------ Results of the validation ------------
        # Heading
        self.header_label = tkboot.Label(self.tab, text="Verification of the DCC", style="GUI.TLabel", font=(text_widget_font, header_font_size + 1))
        self.labels.append(self.header_label)
        self.header_label.grid(row=0, column=1, padx=3, pady=3)

        self.dcc_validation_display = ScrolledText(self.tab, wrap=tk.WORD, height=30, width=60)
        self.dcc_validation_display.grid(row=1, column=1, rowspan=11, padx=2, pady=2)
        self.dcc_validation_display.config(font=(text_widget_font, text_widget_font_size))

        self.dcc_validation_display.tag_config('passed', foreground='green')
        self.dcc_validation_display.tag_config('not_passed', foreground='red')
        self.dcc_validation_display.tag_config('neutral', foreground='black')

    def include_DCC_data(self, data):        
        ID = data["ID"]
        DCC_data_df = data["df"]
        a = round(float(data["a"]), 4)
        b = round(float(data["b"]), 4)
        self.ausgabe = tkboot.Frame(self.tabs[1])
        self.ausgabe.grid(row=10, column=0, padx=5, pady=2)
        # Delete previous output, if any
        if hasattr(self, 'ausgabe_a'):
            self.ausgabe_a.destroy()
        self.ausgabe_a = tkboot.Label(self.ausgabe, text=f"a: {a}", font=(text_widget_font, text_widget_font_size))
        self.ausgabe_a.grid(row=0, column=0, padx=5, pady=2)
        # Delete previous output, if any
        if hasattr(self, 'ausgabe_b'):
            self.ausgabe_b.destroy()
        self.ausgabe_b = tkboot.Label(self.ausgabe, text=f"b: {b}", font=(text_widget_font, text_widget_font_size))
        self.ausgabe_b.grid(row=0, column=1, padx=5, pady=2)

        if hasattr(self, 'treeview'):
            self.treeview.destroy()
            self.treeview_frame.destroy()
        self.treeview_frame = tkboot.Frame(self.tabs[1])
        self.treeview_frame.grid(row=11, column=0, padx=5, pady=2)
        self.treeview = tkboot.Treeview(self.treeview_frame, selectmode="none")
        self.treeview.grid(row=0, column=0, padx=5, pady=2)

        self.treeview["columns"] = list(DCC_data_df.columns)
        self.treeview["show"] = "headings"
        style = tkboot.Style()
        style.configure("Treeview", font=(text_widget_font, text_widget_font_size - 1))
        # Adjust line height
        style.configure("Treeview", rowheight=text_widget_font_size + 10)
        style.configure("Treeview.Heading", font=(text_widget_font, text_widget_font_size + 1))

        # Adds column headers
        for col in DCC_data_df.columns:
            self.treeview.heading(col, text=col, anchor="center")
            self.treeview.column(col, width=160, minwidth=140, anchor="center", stretch=tk.NO)

        # Adds data rows
        for row in DCC_data_df.itertuples(index=False):
            self.treeview.insert("", "end", values=row)


    def update_validation_results(self, data):
        # Assignment of the transferred data
        message = data["Message"]
        bool_value = data["value"]
        current_led = data["led"]
        # Determining the level for the text widget
    #TODO: Einfügen der Option LED auf Gelb zu setzen
        if bool_value != None:
            if bool_value:
                level = 'passed'
            else:
                level = 'not_passed'
        else:
            level = 'neutral'
        # Update the text widgets
        self.update_dcc_validation_display(self.dcc_validation_display, message, level)
        # Update of LED-displays
        if current_led != None:
            for led in current_led:
                if bool_value == None:
                    self.leds_for_validation[led].update_color("black")
                elif bool_value:
                    self.leds_for_validation[led].update_color("lightgreen")
                else:
                    self.leds_for_validation[led].update_color("red")
        
    
    def update_dcc_validation_display(self, text_widget, message, level):
        text_widget.insert(tk.END, message + '\n', level)
        text_widget.see(tk.END)

    def update_sensor_LED(self, data):
        id = data["ID"]
        bool_value = data["value"]
        if bool_value:
            self.DCC_validation_LEDs[id].update_color("lightgreen")
        else:
            self.DCC_validation_LEDs[id].update_color("red")

    
    def drop(self, event):
            '''Starts the validation process when a DCC is dropped into the label field'''
            for led in self.leds_for_validation:
                led.update_color("black")
            # Get the file path
            file_path = event.data
            if os.path.isfile(file_path):
                # Extract the file name and display it in the label
                filename = os.path.basename(file_path)
                self.dropDCClabel.config(text=f'Uploaded file: {filename}')
            else:
                self.dropDCClabel.config(text="Invalid file, please try again.")
            
            def performing_validation():
                print("Validation started.")
                DCCv.performDCCvalidation(file_path, self.mode)
            
            # Start valodation in separated Thread
            validation_thread = PM.start_thread(target=performing_validation, name="DCC_validation")
            print(f"Der Validierungsthread wurde gestartet: {validation_thread}")


    def create_sensor_tabs(self):
        for i, sensor in enumerate(self.controller.sensorNamesList ):
            ####################################################################
            ############ Creation and basic configuration of tabs ##############
            ####################################################################
            # Creation of tabs for each sensor
            tab_name = sensor
            self.tab = tkboot.Frame(self.tab_control)
            self.tab_control.add(self.tab, text=tab_name)
            self.tab.grid_rowconfigure(0, weight=1)
            self.tab.grid_columnconfigure(0, weight=1)
            self.tab.grid_columnconfigure(1, weight=1)
            
            # Creation of frames for raw and corrected measurement data
            self.raw_measurement_frame = tkboot.LabelFrame(self.tab, text="Raw Measurement Data")
            self.raw_measurement_frame.grid(row=0, column=0, sticky=tkboot.NSEW, ipadx=5, ipady=5)
            self.raw_measurement_frame.rowconfigure(0, weight=2)
            self.raw_measurement_frame.rowconfigure(1, weight=3)
            self.raw_measurement_frame.columnconfigure(0, weight=1)
            self.raw_measurement_frame.grid_propagate(False)
            self.raw_measurement_frames.append(self.raw_measurement_frame)

            self.corrected_measurement_frame = tkboot.LabelFrame(self.tab, text="Corrected Measurement Data")
            self.corrected_measurement_frame.grid(row=0, column=1, sticky=tkboot.NSEW, ipadx=5, ipady=5)
            self.corrected_measurement_frame.rowconfigure(0, weight=2)
            self.corrected_measurement_frame.rowconfigure(1, weight=3)
            self.corrected_measurement_frame.columnconfigure(0, weight=1)
            self.corrected_measurement_frame.grid_propagate(False)
            self.corrected_measurement_frames.append(self.corrected_measurement_frame)
            
            # Creation of the upper and lower frames in the two measurement data frames
            self.left_top = tkboot.Frame(self.raw_measurement_frame)
            self.left_top.grid(row=0, column=0, sticky=tkboot.NSEW)
            self.left_top.rowconfigure([0, 1], weight=1)
            self.left_top.columnconfigure([0, 1], weight=1)
            self.left_top.grid_propagate(False)

            self.left_plot_frame = tkboot.Frame(self.raw_measurement_frame)
            self.left_plot_frame.grid(row=1, column=0, sticky=tkboot.NSEW)
            self.left_plot_frame.rowconfigure(0, weight=1)
            self.left_plot_frame.columnconfigure(0, weight=1)
            self.left_plot_frame.grid_propagate(False)

            self.right_top = tkboot.Frame(self.corrected_measurement_frame)
            self.right_top.grid(row=0, column=0, sticky=tkboot.NSEW)
            self.right_top.rowconfigure([0, 1], weight=1)
            self.right_top.columnconfigure([0, 1, 2], weight=1)
            self.right_top.grid_propagate(False)

            self.right_plot_frame = tkboot.Frame(self.corrected_measurement_frame)
            self.right_plot_frame.grid(row=1, column=0, sticky=tkboot.NSEW)
            self.right_plot_frame.rowconfigure(0, weight=1)
            self.right_plot_frame.columnconfigure(0, weight=1)
            self.right_plot_frame.grid_propagate(False)

            # Creation of Plot-Apps
            self.plotApp = self.controller.create_plot_apps(sensor, self.left_plot_frame)
            self.DCCplot = self.controller.create_DCCplot_apps(sensor, self.right_plot_frame)     

            self.create_widgets_for_sensor_tabs(self.tab, i)
            

    def create_widgets_for_sensor_tabs(self, tab, id):
        self.label_style = tkboot.Style()
        self.label_style.configure("GUI.TLabel", font=(text_widget_font, text_widget_font_size))  # Initiale Schriftgröße 
        # ---------------- Without DCC ------------------
        BAMlogo = self.load_BAM_logo(self.left_top)
        self.logos.append(BAMlogo)
        BAMlogo.grid(row=0, column=0, sticky=tkboot.NSEW, padx=10, pady=5)
        # Frame for limits
        self.limitFrame = tkboot.Frame(self.left_top, borderwidth=1, relief="solid")
        self.limitFrame.grid(row=0, column=1, padx=3, pady=3, ipadx=5, ipady=5)
        self.frames.append(self.limitFrame)
        self.limitFrame.rowconfigure([0, 1], weight=1)
        self.limitFrame.columnconfigure([0, 1], weight=1)   
        
        # ------ Inputfields ------
        # Input field for the upper limit value
        self.input_field_upper_limit = InputFieldWidget(self.limitFrame, "Upper Limit:", id)
        self.input_field_upper_limit.grid(row=0, column=0, padx=5, pady=5, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.input_field_upper_limit)
        self.input_upper_limits.append(self.input_field_upper_limit)
        # Input field for the lower limit value
        self.input_field_lower_limit = InputFieldWidget(self.limitFrame, "Lower Limit:", id)
        self.input_field_lower_limit.grid(row=1, column=0, padx=5, pady=5, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.input_field_lower_limit)
        self.input_lower_limits.append(self.input_field_lower_limit)
        # ------ Display fields ------
        # Upper limit output
        self.upper_acceptance_value = OutputFieldWidget(self.limitFrame, "Upper limit of acceptance:")
        self.upper_acceptance_value.grid(row=0, column=1, padx=5, pady=5, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.upper_acceptance_value)
        self.output_upper_acceptance.append(self.upper_acceptance_value)
        # Lower limit output
        self.lower_acceptance_value = OutputFieldWidget(self.limitFrame, "Lower limit of acceptance:")
        self.lower_acceptance_value.grid(row=1, column=1, padx=5, pady=5, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.lower_acceptance_value)
        self.output_lower_acceptance.append(self.lower_acceptance_value)
        # Frame for midlle line
        self.middle_frame = tkboot.Frame(self.left_top)
        self.middle_frame.grid(row=1, column=0, columnspan=2, sticky=tkboot.NSEW)  
        self.frames.append(self.middle_frame)
        self.middle_frame.rowconfigure(0, weight=1)
        self.middle_frame.columnconfigure([0, 1, 2], weight=1)
        # Display of the measured temperature value        
        self.mesTemp = OutputFieldWidget(self.middle_frame, "Measured Temperature /°C:")
        self.mesTemp.grid(row=0, column=0, padx=2, pady=2, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.mesTemp)
        self.output_measured_temps.append(self.mesTemp)
        # Display of the specification 
        self.show_specification = OutputFieldWidget(self.middle_frame, "Specification /K:")
        self.show_specification.grid(row=0, column=1, padx=2, pady=2, sticky=tkboot.NSEW)
        self.custom_widgets.append(self.show_specification)
        self.output_specifications.append(self.show_specification)
        # LED-Display for raw data
        self.led_raw_frame = tkboot.Frame(self.middle_frame)
        self.led_raw_frame.grid(row=0, column=2, padx=2, pady=2, sticky=tkboot.NSEW)
        self.led_raw_title = tkboot.Label(self.led_raw_frame, text="Measurement within acceptance:", style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
        self.led_raw_title.grid(row=0, column=2, padx=2, pady=2, sticky=tkboot.S)
        self.led_raw = LEDwidget(master=self.led_raw_frame, size=0.8)
        self.led_raw.canvas.get_tk_widget().grid(row=1, column=2, padx=10, pady=0, ipadx=0, ipady=0)
        self.leds.append(self.led_raw)
        
        # Display Plot
        self.plot_rawData = self.plotApp.get_canvas()
        self.plot_rawData.config(width=canvas_size[0], height=canvas_size[1])
        self.plot_rawData.grid(row=0, column=0)
        # Bandwidth output
        self.band_width = OutputFieldWidget(self.left_plot_frame, "Acceptance Band Width /K:")
        self.band_width.grid(row=0, column=0, padx=5, pady=5, sticky=tkboot.E)
        self.custom_widgets.append(self.band_width)
        self.band_width_list.append(self.band_width)

        # ---------------------------- Corrected data ------------------------------
        # Switch for activation
        self.switch = SwitchWidget(self.right_top, id)
        self.switch.toggle_switch.grid(row=0, column=0, padx=15, pady=5, sticky=tkboot.NSEW)
        self.DCCswitsches.append(self.switch)
        self.MD.update_switches({"ID": id, "value": self.switch.toggle_var.get()})   
        # --------- Outputfields ----------
        self.corr_limitFrame = tkboot.Frame(self.right_top, borderwidth=1, relief="solid")
        self.corrected_limit_frames.append(self.corr_limitFrame)
        self.corr_limitFrame.rowconfigure(0, weight=1)
        self.corr_limitFrame.columnconfigure(0, weight=1)
        # Outputfield for upper limit
        self.upper_acceptance_label_corrected = OutputFieldWidget(self.corr_limitFrame, "Upper limit of acceptance:")
        self.custom_widgets.append(self.upper_acceptance_label_corrected)
        self.output_upper_acceptanceDCC.append(self.upper_acceptance_label_corrected)
        # Outputfield for lower limit
        self.lower_acceptance_value_corrected = OutputFieldWidget(self.corr_limitFrame, "Lower limit of acceptance:")
        self.custom_widgets.append(self.lower_acceptance_value_corrected)        
        self.output_lower_acceptanceDCC.append(self.lower_acceptance_value_corrected)
        ### Validation LED
        self.validation_frame = tkboot.LabelFrame(self.right_top, text = "Validation", style="GUI.TLabelframe")
        self.validation_frames.append(self.validation_frame)
        self.DCC_validationLED = LEDwidget(master=self.validation_frame, size=0.6)
        self.DCC_validation_LEDs.append(self.DCC_validationLED)
        ### Frame middle line
        self.corr_middle_frame = tkboot.Frame(self.right_top)
        self.corr_middle_frames.append(self.corr_middle_frame)
        self.corr_middle_frame.rowconfigure(0, weight=1)
        self.corr_middle_frame.columnconfigure([0, 1, 3], weight=1)

        # Display field for the corrected temperature
        self.show_corrected_temp = OutputFieldWidget(self.corr_middle_frame, "Corrected Temperature /°C:")
        self.custom_widgets.append(self.show_corrected_temp)
        self.corrected_temps.append(self.show_corrected_temp)
        # Display field for uncertainty
        self.show_uncertainty = OutputFieldWidget(self.corr_middle_frame, "Uncertainty /K:")
        self.custom_widgets.append(self.show_uncertainty)
        self.uncertainties.append(self.show_uncertainty)
        # LED display for the corrected data
        self.ledDCC_frame = tkboot.Frame(self.corr_middle_frame)
        self.ledDCC_frame.grid(row=0, column=2, padx=2, pady=2, sticky=tkboot.NSEW)
        self.ledDCC_title = tkboot.Label(self.ledDCC_frame, text="Quality assured process conformity:", style="GUI.TLabel", font=(text_widget_font, text_widget_font_size))
        self.ledDCC_title_list.append(self.ledDCC_title)
        self.ledDCC_title.grid(row=0, column=2, padx=2, pady=2, sticky=tkboot.S)
        self.led_DCC = LEDwidget(master=self.ledDCC_frame, size=0.8)
        self.ledsDCC.append(self.led_DCC)    
        ### Placeholder for the second plot, if it is hidden
        self.placeholder = PlaceholderWidget(self.right_plot_frame, id)
        self.placeholder.grid(row=1, column=0, padx=10, pady=5, sticky=tkboot.EW)
        self.placeholder_list.append(self.placeholder)
        self.logger.info(f"Der Platzhalter wurde erfolgreich erstellt: {self.placeholder}")
        # Output bandwidth
        self.band_width_DCC = OutputFieldWidget(self.right_plot_frame, "Acceptance Band Width /K:")
        self.custom_widgets.append(self.band_width_DCC)
        self.band_width_list_DCC.append(self.band_width_DCC)
    
    def toggle_plot(self, data):
        print(f"data sieht so aus {data} und hat den Typ: {type(data)}")
        counter = data["ID"]
        switch_boolean = data["value"]
        print(f"Der Wert des Schalters {counter}: {switch_boolean}")
        if switch_boolean:
            self.placeholder_list[counter].grid_remove()
            print(f"Der Platzhalter {self.placeholder_list[counter]} wurde ausgeblendet.")
            ######## Elements to be displayed ########
            # Limits
            self.corrected_limit_frames[counter].grid(row=0, column=1, padx=5, pady=5)
            self.output_upper_acceptanceDCC[counter].grid(row=0, column=0, padx=5, pady=5)
            self.output_lower_acceptanceDCC[counter].grid(row=1, column=0, padx=5, pady=5)
            # Validation
            self.validation_frames[counter].grid(row=0, column=2, padx=5, pady=5)
            self.validation_frames[counter].rowconfigure(0, weight=1)
            self.DCC_validation_LEDs[counter].canvas.get_tk_widget().grid(row=0, column=0)
            # Middle display line
            self.corr_middle_frames[counter].grid(row=1, column=0, columnspan= 3, sticky=tkboot.NSEW, padx=5, pady=20)
            self.corrected_temps[counter].grid(row=0, column=0, padx=5, pady=5, ipadx=0, ipady=5, sticky=tkboot.NSEW)
            self.uncertainties[counter].grid(row=0, column=1, padx=5, pady=5, ipadx=0, ipady=5, sticky=tkboot.NSEW)
            self.ledDCC_title.grid(row=0, column=2, padx=2, pady=2, sticky=tkboot.S)
            self.ledsDCC[counter].canvas.get_tk_widget().grid(row=1, column=2, padx=10, pady=0, ipadx=0, ipady=0)
            # Plot
            self.plot_correctedData_canvas = self.controller.DCCplotApps[counter].get_canvas()
            self.plot_correctedData_canvas.config(width=canvas_size[0], height=canvas_size[1])
            self.plot_correctedData_canvas.grid(row=0, column=0)
            self.band_width_list_DCC[counter].grid(row=0, column=0, sticky=tkboot.E, padx=5, pady=5)
            
        else:
            # Elements to be hidden
            self.corrected_limit_frames[counter].grid_remove()
            self.output_upper_acceptanceDCC[counter].grid_remove()
            self.output_lower_acceptanceDCC[counter].grid_remove()
            self.validation_frames[counter].grid_remove()
            self.DCC_validation_LEDs[counter].canvas.get_tk_widget().grid_remove()
            self.corr_middle_frames[counter].grid_remove()
            self.corrected_temps[counter].grid_remove()
            self.uncertainties[counter].grid_remove()
            self.ledDCC_title.grid_remove()
            self.plot_correctedData_canvas = self.controller.DCCplotApps[counter].get_canvas()
            self.plot_correctedData_canvas.grid_remove()
            self.ledsDCC[counter].canvas.get_tk_widget().grid_remove()
            self.band_width_list_DCC[counter].grid_remove()
    
    def handle_temp_range_error(self, data):
        id = data["ID"]
        value = data["value"]
        self.toggle_plot(data)
        if not value:            
            self.out_of_cal_range_field = tk.Label(self.corrected_measurement_frames[id], text = "Out of calibrated range!", font=("Arial", 30))
            self.out_of_cal_range_field.grid(row=1, column=1, padx=10, pady=10, sticky=tkboot.NSEW)
        else:
            self.out_of_cal_range_field.grid_remove()
    
    
    def publish_event(self, event):
        # Publish event via EventBus
        try:
            if event == "data_source_changed":
                self.EB.publish(event, self.source_var.get())
                print(f"Event published: {event} with data: {self.source_var.get()}")
            elif event == "comport_selected":
                print(f"Der ausgewählte COM-Port ist: {self.com_port_var.get()}")
                self.EB.publish(event, self.com_port_var.get())
                print(f"Event published: {event} with data: {self.com_port_var.get()}")                
                self.source_var.set("Livedata")
                print(f"Die Datenquelle wurde auf 'Livedata' gesetzt: {self.source_var.get()}")
        except Exception as e:
            print(f"Fehler beim Veröffentlichen des Events {event}: {e} mit Typ: {type(e)}")              
    
    

##################### Hilfsfunktionen beim Programmieren #####################
    def list_active_threads(self):
            print("List of active threads:")
            for thread in threading.enumerate():
                print(f"Thread: {thread}")
            return threading.enumerate()



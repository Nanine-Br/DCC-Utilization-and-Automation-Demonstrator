import matplotlib
matplotlib.use("TkAgg")
import ttkbootstrap as tkboot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox
# Own modules
from Instance_Manager import IM
from Global import text_widget_font_size, text_widget_font, placeholder_size
EB = IM.get_instance("EB")

plt.rcParams["figure.max_open_warning"] = 30

class LEDwidget(tkboot.Frame):
    def __init__(self, master, color = "black", size=1.0):
        super().__init__(master)
        self.master = master
        self.color = color
        self.r = 1.5
        self.fig = plt.figure(figsize=(size, size), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.create_widgets()
    
    def update_color(self, new_color):
        if self.color == new_color:
            return
        self.color = new_color
        self.update_plot()

    def create_widgets(self):
        # Data for plotting the sphere
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 20)
        self.x = np.outer(self.r*np.cos(u), self.r*np.sin(v))
        self.y = np.outer(self.r*np.sin(u), self.r*np.sin(v))
        self.z = np.outer(self.r*np.ones(np.size(u)), self.r*np.cos(v))

        # Plot the sphere
        self.surface = self.ax.plot_surface(self.x, self.y, self.z, color=self.color)

        width, height = 1, 1 # Width and height of the plot as a fraction of the figure size
        left = (1 - width)/2
        bottom = (1 - height)/2
        self.ax.set_position([left, bottom, width, height])
        self.ax.set_box_aspect([1, 1, 1])  # [x, y, z] Ratio
        self.ax.set_xlim([-self.r, self.r])
        self.ax.set_ylim([-self.r, self.r])
        self.ax.set_zlim([-self.r, self.r])
        self.ax.set_axis_off()  # Hide the axes

        self.canvas.draw()
    
    def destroy(self):
        self.canvas.get_tk_widget().destroy()  # Remove the canvas widget from the Tkinter layout
        super().destroy()

    def update_plot(self):
            self.surface.remove()  # Remove the old surface
            self.surface = self.ax.plot_surface(self.x, self.y, self.z, color=self.color)  # New surface with updated color
            self.canvas.draw()
    

class SwitchWidget(tkboot.Frame):
    def __init__(self, master, instance_id):
        super().__init__(master)
        self.master = master
        self.id = instance_id
        self.create_toggle_switch(self.master)

    def create_toggle_switch(self, tab):
        self.toggle_var = tkboot.BooleanVar()

        def on_toggle():
            EB.publish("DCC_toggle_switch_changed", {"ID": self.id, "value": self.toggle_var.get()})

        self.toggle_switch = tkboot.Checkbutton(tab, text="Include DCC", style="success.Roundtoggle.Toolbutton", variable=self.toggle_var, command=on_toggle)
        

class PlaceholderWidget(tkboot.Frame):
    def __init__(self, master, ID):
        super().__init__(master)
        self.master = master
        self.id = ID
        self.create_widget()

    def create_widget(self):
        self.placeholder = tk.Frame(master=self, background="black", width=placeholder_size, height=placeholder_size/2)
        self.placeholder.grid()

class InputFieldWidget(tkboot.Frame):
    def __init__(self, master, field_label, instance_id):
        super().__init__(master)
        self.master = master
        self.field_label = field_label
        self.instance_id = f"{field_label.replace(':', '')}_{instance_id}"
        # Create style for the widget
        self.style = tkboot.Style()
        self.style.configure("Custom.TLabel", font=(text_widget_font, text_widget_font_size))  # Initial font size
        self.create_widgets()

    def create_widgets(self):
        self.label = tkboot.Label(self, text=self.field_label, font=(text_widget_font, text_widget_font_size))
        self.label.grid()
        self.input_value = tkboot.DoubleVar()
        self.input_field = tk.Entry(self, textvariable=self.input_value, width=15, bd=2, relief="sunken", font=(text_widget_font, text_widget_font_size))
        self.input_field.grid()
        self.input_field.bind("<FocusOut>", self.on_focus_out)  # Bind to focus out event
        self.input_field.bind("<Return>", self.on_enter_pressed)  # Bind to Enter key event

# TODO: Möglicherweise wird on_focus_out und on_enter_pressed nicht benötigt, sondern publish_value kann direkt aufgerufen werden
    def on_focus_out(self, event):
        self.publish_value()

    def on_enter_pressed(self, event):
        self.publish_value()
    
    def publish_value(self, *args):
        '''This method is called whenever the value changes and publishes the new value in the EventBus.'''
        value = self.input_value.get()
        if type(value) == float or type(value) == int:
            EB.publish("limit_changed", {"instance_id": self.instance_id, "value": value})
        else:
            messagebox.showerror("Error", "Please enter a float or an integer, not a string.")     
    
    def update_font_size(self, size):
        font = ("Helvetica", size)
        self.label.config(font=font)
        self.input_field.config(font=font)


class OutputFieldWidget(tkboot.Frame):
    def __init__(self, master, field_label):
        super().__init__(master)
        self.master = master
        self.field_label = field_label
        # Stil für das Widget erstellen
        self.style = tkboot.Style()
        self.style.configure("Custom.TLabel", font= (text_widget_font, text_widget_font_size), )  # Initiale Schriftgröße
        self.create_widgets()

    def create_widgets(self):
        self.label = tkboot.Label(self, text=self.field_label, font=(text_widget_font, text_widget_font_size))
        self.label.grid()
        self.string_var = tkboot.StringVar()
        self.output_field = tkboot.Label(self, textvariable=self.string_var,  width=15, border=2, relief="sunken", text=f"{self.string_var}", anchor="center")
        self.output_field.config(font=(text_widget_font, text_widget_font_size))
        self.output_field.grid()

    def set_output_field(self, value):
        self.string_var.set(value)

    def update_output_field(self, value):
        self.string_var.set(value)
        self.output_field.update()
    
    def update_font_size(self, size):
        # Update font size in style
        font = (text_widget_font, size)
        self.label.config(font=font)
        self.style.configure("Custom.TLabel", font=font)
        self.output_field.config(font=font)
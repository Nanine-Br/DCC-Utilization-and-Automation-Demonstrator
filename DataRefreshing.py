from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
# Own modules
from Instance_Manager import IM
from Global import plot_fig_size, number_of_measurement_values_used_in_plot
from datetime import datetime as dt


class LivePlotApp:
    def __init__(self, sensor, parent):
        self.logger = IM.get_instance("logger")
        self.plot_fig_size = plot_fig_size
        self.init_plot(parent)  # Initialize Plot
        
    def init_plot(self, parent):
        self.figure, self.ax = plt.subplots(figsize=self.plot_fig_size, dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.logger.info(f"Eine Figur (Plot) mit Namen {self.figure} und Typ {type(self.figure)} wurde erstellt.")
        self.ax.plot([], [], label='Temperature')
        self.ax.plot([], [], label='Upper Limit')
        self.ax.plot([], [], label='Lower Limit')
        self.ax.plot([], [], label='Upper Limit of Acceptance')
        self.ax.plot([], [], label='Lower Limit of Acceptance')

        self.ax.legend(loc='upper right', bbox_to_anchor=(1.4, 0.8))
        self.ax.set_position([0.1, 0.15, 0.6, 0.7])
        self.canvas.draw()

    def get_canvas(self):
        return self.canvas.get_tk_widget()

    def update_plot(self, data_df, upper_limit, lower_limit, upper_limit_acceptance, lower_limit_acceptance, title="", ylim=None):
        if isinstance(data_df, pd.DataFrame) and len(data_df) > 0:
            self.ax.clear()

            if len(data_df) > number_of_measurement_values_used_in_plot:
                data = data_df.iloc[-number_of_measurement_values_used_in_plot:]
            else:
                data = data_df

            # Labeling of the x-axis
            num_ticks = min(len(data["timestamp"]), 5)  # Limit the number of xticks to 5
            tick_positions = list(range(0, len(data["timestamp"]), max(1, len(data["timestamp"]) // num_ticks)))
            valid_tick_positions = [pos for pos in tick_positions if pos < len(data["timestamp"])]  # Only use valid indexes
            self.ax.set_xticks(valid_tick_positions)  # Sets the xticks to the calculated positions
            self.ax.set_xticklabels([data["timestamp"].iloc[pos] for pos in valid_tick_positions], rotation=45, ha='right')  # sets xticklabels
            
            data.plot(x="timestamp", y="temperature", ax=self.ax)
            self.ax.axhline(y=upper_limit, color='r', linestyle=':', label='Upper Limit')
            self.ax.axhline(y=lower_limit, color='r', linestyle=':', label='Lower Limit')
            self.ax.axhline(y=upper_limit_acceptance, color='g', linestyle='--', label='Upper Limit of Acceptance')
            self.ax.axhline(y=lower_limit_acceptance, color='g', linestyle='--', label='Lower Limit of Acceptance')
            
            if ylim is not None:
                self.ax.set_ylim(ylim)
            else:
                self.ax.relim()
                self.ax.autoscale(True, axis='y')  # Automatic scaling of the y-axis

            self.ax.set_title(title)
            self.ax.title.set_fontsize(16)
            self.ax.set_xlabel('Timestamp')
            self.ax.set_ylabel('Temperature /°C')
            self.ax.legend(loc='upper right', bbox_to_anchor=(1.5, 0.9))
            self.ax.set_position([0.1, 0.15, 0.6, 0.7])
            self.ax.grid(True, which='both')
        else:
            print("There is no data for plotting.")
            self.logger.warning("There is no data for plotting.")
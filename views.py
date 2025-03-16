from tkinter.ttk import Treeview, Button


class SelectChromecastView:
    def __init__(self, treeview: Treeview):
        self.casts_headers = ("Model name", "Friendly name", "IP address")
        treeview.config(columns=self.casts_headers)
        for col in self.casts_headers:
            treeview.column(col)
            treeview.heading(col, text=col)

    def add_cast(
            self,
            treeview: Treeview,
            model_name: str,
            friendly_name: str,
            host: str):
        treeview.insert("", "end", values=(model_name, friendly_name, host))

    def get_casts_data(self):
        ret = []
        for cast in self.casts:
            cast_values = []
            for cast_accessor in self._cast_accessors:
                cast_value = cast
                for cast_attr in cast_accessor.split("."):
                    cast_value = getattr(cast_value, cast_attr)
                cast_values.append(cast_value)
            ret.append(dict(zip(self.casts_headers, cast_values)))
        return ret


def toggle_button(sunken_condition: bool, tk_button: Button):
    if sunken_condition:
        tk_button.config(relief="sunken")
    else:
        tk_button.config(relief="raised")

"""Rural Road Pathfinder - graphical interface (tkinter, +10% GUI marks).

Two tabs:
  Find Route    - pick places and criteria, see the route (calls routing.pl)
  Roads (Admin) - list roads, add / edit a road, change the season (rules.pl)

All reasoning is still done by Prolog; this file only collects input and
shows results. It reuses roads.py (admin logic) and main.py (route query).
Run:  python gui.py
"""
import tkinter as tk
from tkinter import ttk, messagebox

import roads            # P1: load/save roads, validation
import main as cli      # P3: find_route() and the criteria lists


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rural Road Pathfinder")
        self.geometry("980x600")
        self.roads, self.season = [], "dry"

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.route_tab = ttk.Frame(tabs, padding=12)
        self.admin_tab = ttk.Frame(tabs, padding=12)
        tabs.add(self.route_tab, text="Find Route")
        tabs.add(self.admin_tab, text="Roads (Admin)")

        self.build_route_tab()
        self.build_admin_tab()
        self.refresh()

    # ------------------------------------------------------------ data

    def refresh(self):
        """Reload every road through Prolog and update both tabs."""
        try:
            self.roads, self.season = roads.load_roads()
        except SystemExit as error:
            messagebox.showerror("Prolog error", str(error))
            return
        places = sorted({p for r in self.roads for p in (r["source"], r["dest"])})
        self.src_box["values"] = places
        self.dst_box["values"] = places
        self.season_label.config(text=f"Current season: {self.season}")
        self.season_var.set(self.season)

        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.roads):
            conds = ",".join(r["conditions"]) or "none"
            if r["pothole_inches"]:
                conds += f" ({roads.pl_number(r['pothole_inches'])} in)"
            if r["seasonal"] == "rainy":
                conds += " [seasonal]"
            tag = "closed" if r["effective_status"] == "closed" else "open"
            self.tree.insert("", "end", iid=str(i), tags=(tag,), values=(
                r["source"], r["dest"], roads.pl_number(r["km"]), r["mins"],
                r["effective_mins"], r["type"], r["direction"],
                r["effective_status"], conds))

    # ------------------------------------------------------- route tab

    def build_route_tab(self):
        f = self.route_tab
        ttk.Label(f, text="From:").grid(row=0, column=0, sticky="w", pady=4)
        self.src_box = ttk.Combobox(f, width=30, state="readonly")
        self.src_box.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(f, text="To:").grid(row=1, column=0, sticky="w", pady=4)
        self.dst_box = ttk.Combobox(f, width=30, state="readonly")
        self.dst_box.grid(row=1, column=1, sticky="w", padx=8)

        goal_frame = ttk.LabelFrame(f, text="Route type", padding=8)
        goal_frame.grid(row=2, column=0, columnspan=2, sticky="we", pady=8)
        self.goal = tk.StringVar(value="Shortest distance")
        for label in cli.GOALS:
            ttk.Radiobutton(goal_frame, text=label, value=label,
                            variable=self.goal).pack(anchor="w")

        avoid_frame = ttk.LabelFrame(f, text="Avoid", padding=8)
        avoid_frame.grid(row=3, column=0, columnspan=2, sticky="we")
        self.avoid = {}
        for label in cli.AVOIDS:
            self.avoid[label] = tk.BooleanVar(value=(label == "Closed roads"))
            ttk.Checkbutton(avoid_frame, text=label,
                            variable=self.avoid[label]).pack(anchor="w")

        ttk.Button(f, text="Find route", command=self.find_route).grid(
            row=4, column=0, columnspan=2, pady=12)

        result = ttk.LabelFrame(f, text="Result", padding=8)
        result.grid(row=0, column=2, rowspan=5, sticky="nsew", padx=16)
        f.columnconfigure(2, weight=1)
        self.result = tk.Label(result, text="Choose places and press Find route.",
                               justify="left", anchor="nw", wraplength=420,
                               font=("Segoe UI", 11))
        self.result.pack(fill="both", expand=True)

    def find_route(self):
        src, dst = self.src_box.get(), self.dst_box.get()
        if not src or not dst:
            messagebox.showwarning("Missing place", "Choose both a start and a destination.")
            return
        if src == dst:
            messagebox.showwarning("Same place", "Start and destination are the same place.")
            return
        avoids = [value for label, value in cli.AVOIDS.items() if self.avoid[label].get()]
        try:
            found = cli.find_route(src, dst, cli.GOALS[self.goal.get()], avoids)
        except ValueError as error:
            messagebox.showwarning("Unknown place", str(error))
            return
        except SystemExit as error:
            messagebox.showerror("Prolog error", str(error))
            return

        if found is None:
            self.result.config(text="No path is available with those criteria.", fg="#b00020")
            return
        text = (f"Algorithm (chosen by Prolog): {found['algorithm']}\n\n"
                f"Route:\n  " + "\n  -> ".join(found["places"]) + "\n\n"
                f"Total distance: {found['km']:g} km\n"
                f"Total estimated time: {found['mins']} min")
        if "closed" not in avoids:
            text += "\n\nNote: closed roads were allowed, so this route may use one."
        self.result.config(text=text, fg="black")

    # ------------------------------------------------------- admin tab

    def build_admin_tab(self):
        f = self.admin_tab
        columns = ("Source", "Dest", "Km", "Base", "Eff", "Type", "Dir", "Now", "Conditions")
        self.tree = ttk.Treeview(f, columns=columns, show="headings", height=15,
                                 selectmode="browse")
        widths = (140, 140, 45, 50, 45, 70, 70, 60, 280)
        for name, width in zip(columns, widths):
            self.tree.heading(name, text=name)
            self.tree.column(name, width=width, anchor="w")
        self.tree.tag_configure("closed", foreground="#b00020")
        self.tree.pack(fill="both", expand=True)

        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="Add road", command=lambda: RoadDialog(self, None)).pack(side="left")
        ttk.Button(bar, text="Edit selected", command=self.edit_selected).pack(side="left", padx=6)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")

        self.season_label = ttk.Label(bar, text="")
        self.season_label.pack(side="right", padx=8)
        ttk.Button(bar, text="Set season", command=self.set_season).pack(side="right")
        self.season_var = tk.StringVar(value="dry")
        ttk.Combobox(bar, textvariable=self.season_var, values=roads.SEASONS,
                     width=8, state="readonly").pack(side="right", padx=6)

        ttk.Label(f, text="Base = stored minutes, Eff = minutes after the +5 rule, "
                          "Now = status after closure rules (red = closed).").pack(anchor="w")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Edit road", "Select a road in the table first.")
            return
        RoadDialog(self, self.roads[int(selected[0])])

    def set_season(self):
        new = self.season_var.get()
        try:
            roads.save_roads(self.roads, new)
        except OSError as error:
            messagebox.showerror("File error", str(error))
            return
        self.refresh()
        closed = [f"{r['source']} - {r['dest']}" for r in self.roads
                  if "closed in rainy season" in r["reasons"]]
        messagebox.showinfo("Season", f"Season set to {new}.\n"
                            f"Seasonal roads closed: {', '.join(closed) or 'none'}.")


class RoadDialog(tk.Toplevel):
    """Add a new road (road=None) or edit an existing one."""

    def __init__(self, app, road):
        super().__init__(app)
        self.app, self.road = app, road
        self.title("Add road" if road is None else "Edit road")
        self.resizable(False, False)
        self.grab_set()
        d = road or {}
        pad = {"padx": 8, "pady": 3}

        self.vars = {
            "source": tk.StringVar(value=d.get("source", "")),
            "dest": tk.StringVar(value=d.get("dest", "")),
            "km": tk.StringVar(value=roads.pl_number(d["km"]) if d else ""),
            "mins": tk.StringVar(value=str(d.get("mins", ""))),
            "pothole_inches": tk.StringVar(
                value=roads.pl_number(d["pothole_inches"]) if d else "0"),
            "type": tk.StringVar(value=d.get("type", "paved")),
            "status": tk.StringVar(value=d.get("status", "open")),
            "direction": tk.StringVar(value=d.get("direction", "two_way")),
            "seasonal": tk.StringVar(value=d.get("seasonal", "none")),
        }
        text_rows = (("Source", "source"), ("Destination", "dest"), ("Distance (km)", "km"),
                     ("Base minutes (no delays)", "mins"),
                     ("Deepest pothole (inches, 0 = none)", "pothole_inches"))
        row = 0
        for label, key in text_rows:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", **pad)
            entry = ttk.Entry(self, textvariable=self.vars[key], width=28)
            entry.grid(row=row, column=1, **pad)
            if road is not None and key in ("source", "dest"):
                entry.config(state="disabled")      # places stay fixed when editing
            row += 1
        for label, key, values in (("Road type", "type", roads.ROAD_TYPES),
                                   ("Status", "status", roads.STATUSES),
                                   ("Direction", "direction", roads.DIRECTIONS),
                                   ("Seasonally blocked", "seasonal", roads.SEASONAL)):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Combobox(self, textvariable=self.vars[key], values=values,
                         width=25, state="readonly").grid(row=row, column=1, **pad)
            row += 1

        cond_frame = ttk.LabelFrame(self, text="Conditions", padding=6)
        cond_frame.grid(row=row, column=0, columnspan=2, sticky="we", **pad)
        self.cond_vars = {}
        for c in roads.CONDITIONS:
            self.cond_vars[c] = tk.BooleanVar(value=c in d.get("conditions", []))
            ttk.Checkbutton(cond_frame, text=c, variable=self.cond_vars[c]).pack(anchor="w")
        row += 1

        buttons = ttk.Frame(self)
        buttons.grid(row=row, column=0, columnspan=2, pady=8)
        ttk.Button(buttons, text="Save", command=self.save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")

    def save(self):
        v = self.vars
        try:
            km, mins = float(v["km"].get()), int(v["mins"].get())
            inches = float(v["pothole_inches"].get())
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "Distance and pothole depth must be numbers; "
                                 "minutes must be a whole number.", parent=self)
            return
        known = self.app.roads
        if self.road is None:
            source = roads.canon_place(known, roads.clean_name(v["source"].get()))
            dest = roads.canon_place(known, roads.clean_name(v["dest"].get()))
            if roads.find_road(known, source, dest):
                messagebox.showerror("Duplicate", "A road between those places already "
                                     "exists. Select it and use Edit.", parent=self)
                return
        else:
            source, dest = self.road["source"], self.road["dest"]

        new = {"source": source, "dest": dest, "km": km, "mins": mins,
               "type": v["type"].get(),
               "conditions": [c for c, var in self.cond_vars.items() if var.get()],
               "pothole_inches": inches, "status": v["status"].get(),
               "direction": v["direction"].get(), "seasonal": v["seasonal"].get()}
        errors = roads.validate_road(new)
        if errors:
            messagebox.showerror("Not saved", "\n".join(errors), parent=self)
            return

        if self.road is None:
            updated = known + [new]
        else:
            updated = [new if r is self.road else r for r in known]
        try:
            roads.save_roads(updated, self.app.season)
        except OSError as error:
            messagebox.showerror("File error", str(error), parent=self)
            return
        self.app.refresh()
        saved = roads.find_road(self.app.roads, source, dest)
        messagebox.showinfo("Saved to roads.pl", roads.describe(saved) if saved else "Saved.",
                            parent=self)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
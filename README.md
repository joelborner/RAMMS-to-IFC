# RAMMS-to-IFC
Python script to convert RAMMS Rockfall trajectories into IFC format to visualize in BIM projects.

Written by Joël Borner, WSL Institute for Snow and Avalanche Research SLF
joel.borner@slf.ch


To run:
- Clone repository and run ramms2ifc_GUI.py
- Add Trajectory files (*.rts) from RAMMS Simulation to list
- Add rock geometry (*.pts) to list
- Specify gap length between visualised time steps
- Specify color of visualised rocks (default gray or colorbar energy/jumpheight)
- Click "Convert to IFC"
- Your IFC file containing all selected trajectories is generated in your root directory
- Open IFC in BIM viewer of choice
